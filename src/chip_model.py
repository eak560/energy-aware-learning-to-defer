"""Phase 2: the on-device (ESP32) sentiment model, trained on millions of reviews.

Model: hashed unigrams + bigrams, binary and L2-normalised, optional Naive
Bayes scaling (Wang & Manning 2012) folded into the weights, logistic loss
trained with averaged SGD in chunks. The device stores one int8 weight per
hash bucket: 2^18 buckets = 256 KB, 2^20 = 1 MB.

Text is hashed once at 2^20 buckets and cached as a binary matrix (1-byte
values, ~3.6 GB for 1.94M reviews). Smaller tables are made chunk by chunk
by masking the bucket index, which gives exactly the buckets that hashing
at that size directly would. Nothing larger than one chunk is ever
converted to floats, so this fits in 18 GB of RAM.

Experiments (all choices use the official val split; test is only
reported, never used to choose):
  1. accuracy vs. training-set size (20k -> 1.94M reviews)
  2. NB scaling on/off and 256 KB vs 1 MB at full size
  3. leak ablation: adding reviews of official test-set movies
  4. extra-data ablation: adding 1.25M long Amazon reviews

    python -I src/chip_model.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import scipy.sparse as sp  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from sklearn.feature_extraction.text import HashingVectorizer  # noqa: E402
from sklearn.linear_model import SGDClassifier  # noqa: E402
from sklearn.preprocessing import normalize  # noqa: E402

from common import MODELS_DIR, ROOT, SEED, load_split, metrics, save_json, save_proba  # noqa: E402

CACHE = ROOT / "data" / "cache" / "hashed_2p20"
SPLITS = ROOT / "data" / "pool" / "splits"
MAX_BITS = 20
CHUNK = 100_000


# ---------------------------------------------------------------- hashing + cache

def _hash_chunk(texts):
    hv = HashingVectorizer(n_features=2 ** MAX_BITS, ngram_range=(1, 2), alternate_sign=False,
                           binary=True, norm=None, dtype=np.float32)
    X = hv.transform(texts)
    return X.indices.astype(np.int32), np.diff(X.indptr).astype(np.int32)


def binary_csr(indices, row_nnz=None, indptr=None):
    if indptr is None:
        indptr = np.zeros(len(row_nnz) + 1, dtype=np.int64)
        np.cumsum(row_nnz, out=indptr[1:])
    if indptr[-1] < 2 ** 31:  # keep 32-bit indices: halves memory
        indptr = indptr.astype(np.int32)
    return sp.csr_matrix((np.ones(len(indices), np.int8), indices, indptr),
                         shape=(len(indptr) - 1, 2 ** MAX_BITS))


def cached(name: str, loader):
    """Binary hashed matrix (CSR, 2^20 columns, int8 values) and labels for a named split."""
    path = CACHE / f"{name}.npz"
    if path.exists():
        z = np.load(path)
        return binary_csr(z["indices"], indptr=z["indptr"]), z["labels"]
    t0 = time.perf_counter()
    idx, nnz, labels = [], [], []
    for texts, y in loader():
        steps = range(0, len(texts), 20_000)
        for i, n in Parallel(n_jobs=-1)(delayed(_hash_chunk)(texts[s:s + 20_000]) for s in steps):
            idx.append(i)
            nnz.append(n)
        labels.append(np.asarray(y, dtype=np.int8))
    indices, row_nnz, y = np.concatenate(idx), np.concatenate(nnz), np.concatenate(labels)
    del idx, nnz
    X = binary_csr(indices, row_nnz=row_nnz)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(path, indices=X.indices, indptr=X.indptr, labels=y)
    print(f"hashed {name}: {X.shape[0]:,} reviews, {X.nnz:,} features in {time.perf_counter() - t0:.0f}s", flush=True)
    return X, y


def from_split(name):
    def loader():
        df = load_split(name)
        yield df["text"].tolist(), df["label"].to_numpy()
    return loader


def from_parquet(path):
    def loader():
        for batch in pq.ParquetFile(path).iter_batches(batch_size=200_000, columns=["text", "label"]):
            yield batch.column("text").to_pylist(), batch.column("label").to_numpy()
    return loader


def fold(X: sp.csr_matrix, bits: int) -> sp.csr_matrix:
    """Re-bucket into 2^bits buckets (binary, so a collision stays 1). Use on chunks."""
    if bits == MAX_BITS:
        return X
    Y = sp.csr_matrix((X.data, X.indices & (2 ** bits - 1), X.indptr), shape=(X.shape[0], 2 ** bits))
    Y.sum_duplicates()
    Y.data[:] = 1
    return Y


# ---------------------------------------------------------------- model

def chunks(n_rows, rng=None):
    order = np.arange(n_rows) if rng is None else rng.permutation(n_rows)
    for i in range(0, n_rows, CHUNK):
        yield np.sort(order[i:i + CHUNK])


def nb_ratio(B, y, n_rows, bits, alpha=1.0):
    p = np.full(2 ** bits, alpha)
    q = np.full(2 ** bits, alpha)
    for rows in chunks(n_rows):
        Bc, yc = fold(B[rows], bits), y[rows]
        p += np.asarray(Bc[yc == 1].sum(axis=0)).ravel()
        q += np.asarray(Bc[yc == 0].sum(axis=0)).ravel()
    return np.log((p / p.sum()) / (q / q.sum())).astype(np.float32)


def features(B_chunk, bits, r):
    X = normalize(fold(B_chunk, bits).astype(np.float64))
    if r is not None:
        X.data *= r[X.indices]
    return X


def train(B, y, n_rows, bits, alpha, r, epochs=5):
    clf = SGDClassifier(loss="log_loss", alpha=alpha, average=True, random_state=SEED)
    rng = np.random.default_rng(SEED)
    for _ in range(epochs):
        for rows in chunks(n_rows, rng):
            clf.partial_fit(features(B[rows], bits, r), y[rows], classes=[0, 1])
    return clf


def device_weights(clf, r):
    """What the ESP32 stores: NB scaling folded in, then int8 with one float scale."""
    w = clf.coef_[0] * (r if r is not None else 1.0)
    scale = float(np.abs(w).max() / 127)
    return np.clip(np.round(w / scale), -127, 127).astype(np.int8), scale, float(clf.intercept_[0])


def device_proba(B, bits, weights):
    q, scale, bias = weights
    w = q.astype(np.float32) * scale
    out = np.empty(B.shape[0], dtype=np.float32)
    for rows in chunks(B.shape[0]):
        out[rows] = normalize(fold(B[rows], bits).astype(np.float32)) @ w + bias
    return 1 / (1 + np.exp(-out))


def alpha_grid(n_rows):
    # More data needs less regularisation, so the grid slides down with size.
    if n_rows >= 1_000_000:
        return [3e-9, 1e-8, 3e-8, 1e-7]
    if n_rows >= 200_000:
        return [1e-8, 3e-8, 1e-7, 3e-7, 1e-6]
    return [1e-7, 3e-7, 1e-6, 3e-6, 1e-5]


def fit_and_score(B, y, n_rows, B_val, y_val, bits, alphas, use_nb=True):
    r = nb_ratio(B, y, n_rows, bits) if use_nb else None
    best = None
    for a in alphas:
        t0 = time.perf_counter()
        weights = device_weights(train(B, y, n_rows, bits, a, r), r)
        acc = metrics(y_val, device_proba(B_val, bits, weights) >= 0.5)["accuracy"]
        print(f"    {2 ** bits // 1024}KB nb={use_nb} alpha={a:g} n={n_rows:,}: "
              f"val int8 accuracy {acc:.4f} ({time.perf_counter() - t0:.0f}s)", flush=True)
        if best is None or acc > best["val_accuracy_int8"]:
            best = {"alpha": a, "val_accuracy_int8": acc, "weights": weights}
    best["alpha_at_grid_edge"] = len(alphas) > 1 and best["alpha"] in (alphas[0], alphas[-1])
    return best


# ---------------------------------------------------------------- experiments

def main():
    B_val, y_val = cached("val", from_split("val"))
    B_test, y_test = cached("test", from_split("test"))
    B_def, _ = cached("defer", from_parquet(SPLITS / "defer.parquet"))
    B_maas, y_maas = cached("maas_train", from_split("train"))
    B_pool, y_pool = cached("chip_train", from_parquet(SPLITS / "chip_train.parquet"))
    # Official train rows first, then the pool, so "first n rows" grows the training set.
    B_full = sp.vstack([B_maas, B_pool], format="csr")
    y_full = np.concatenate([y_maas, y_pool])
    del B_pool, B_maas
    n_maas, n_full = len(y_maas), B_full.shape[0]

    results = {"size_curve": [], "full": {}, "ablations": {}}

    print("1. accuracy vs training-set size (256 KB, NB on)", flush=True)
    for n_rows in [n_maas, n_maas + 80_000, n_maas + 280_000, n_maas + 980_000, n_full]:
        best = curve_full = fit_and_score(B_full, y_full, n_rows, B_val, y_val, 18, alpha_grid(n_rows))
        results["size_curve"].append({"train_reviews": int(n_rows), "alpha": best["alpha"],
                                      "alpha_at_grid_edge": best["alpha_at_grid_edge"],
                                      "val_accuracy_int8": best["val_accuracy_int8"]})

    print("2. full size: NB on/off, 256 KB vs 1 MB", flush=True)
    models = {}
    for bits, use_nb in [(18, True), (18, False), (20, True)]:
        key = f"{2 ** bits // 1024}KB_nb{'on' if use_nb else 'off'}"
        if key == "256KB_nbon":
            best = curve_full  # identical to the last point of the size curve
        else:
            best = fit_and_score(B_full, y_full, n_full, B_val, y_val, bits, alpha_grid(n_full), use_nb)
        models[key] = (bits, use_nb, best)
        results["full"][key] = {k: best[k] for k in ("alpha", "alpha_at_grid_edge", "val_accuracy_int8")}

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for key, (bits, _, best) in models.items():
        q, scale, bias = best["weights"]
        np.savez(MODELS_DIR / f"chip_{key}.npz", weights=q, scale=scale, bias=bias, bits=bits, ngram_max=2)

    # The ESP32 runs the 256 KB model; NB on/off is picked by val accuracy.
    main_key = max((k for k in models if k.startswith("256KB")), key=lambda k: models[k][2]["val_accuracy_int8"])
    bits, use_nb, best = models[main_key]
    p = {name: device_proba(B, bits, best["weights"]) for name, B in [("val", B_val), ("test", B_test), ("defer", B_def)]}
    for name, proba in p.items():
        save_proba("chip", name, proba)
    results["main_model"] = {"key": main_key, "bits": bits, "alpha": best["alpha"], "bytes": 2 ** bits,
                             "val": metrics(y_val, p["val"] >= 0.5), "test": metrics(y_test, p["test"] >= 0.5)}
    save_json("chip_model_results.json", results)

    print("3-4. ablations with the main model's settings", flush=True)
    for name, split in [("plus_test_movie_reviews", "test_movies"), ("plus_amazon_long", "amazon_long")]:
        B_extra, y_extra = cached(split, from_parquet(SPLITS / f"{split}.parquet"))
        B_aug = sp.vstack([B_full, B_extra], format="csr")
        y_aug = np.concatenate([y_full, y_extra])
        del B_extra
        m = fit_and_score(B_aug, y_aug, B_aug.shape[0], B_val, y_val, bits, [best["alpha"]], use_nb)
        del B_aug
        results["ablations"][name] = {
            "train_reviews": int(len(y_aug)),
            "val": metrics(y_val, device_proba(B_val, bits, m["weights"]) >= 0.5),
            "test": metrics(y_test, device_proba(B_test, bits, m["weights"]) >= 0.5),
        }
        save_json("chip_model_results.json", results)

    print("main model:", results["main_model"])
    print("ablations:", results["ablations"])


if __name__ == "__main__":
    main()
