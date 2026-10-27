"""Cleaning round 2 for the IMDb pool, after the adversarial review.

Flags every pool review that could leak test information beyond exact copies:
  test_movie   about a movie in the official test set: title+year match against the
               official test movie list (roman-numeral suffixes like "Crash (I) (2004)"
               handled) OR the exact Kaggle movie name of any copied test review
  test_author  written by someone who also wrote a test review (authors of the copies)
  near_dup     shares >= 30% of a val/test review's distinct word 8-grams (edited reposts)

Then builds splits_v2, all movie- and author-disjoint from the test set:
  val_pool     50k balanced reviews from a held-out 5% of movies, length-matched to the
               official test set: a large second validation set for model choices
  defer        300k balanced, held out from chip/hub training (for the deferral router)
  chip_train   the rest, balanced
plus ablation sets: test_movie_reviews, test_author_reviews.

    python -I src/pool_hygiene.py
"""

import json
import multiprocessing as mp
import re
import sys
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from common import ROOT, SEED, clean_text, load_split, save_json  # noqa: E402
from maas_movies import movie_key  # noqa: E402

POOL = ROOT / "data" / "pool"
OUT = POOL / "splits_v2"
K = 8                      # word n-gram size for near-duplicate shingles
NEAR_DUP_SHARE = 0.30      # share of a val/test review's shingles found in a pool review
VAL_MOVIE_MOD = 20         # 1 in 20 eligible movies (5%) goes to val_pool
VAL_SIZE, DEFER_SIZE = 50_000, 300_000
LEN_BINS = np.array([0, 50, 100, 150, 200, 300, 400, 600, 1000, 10**9])

_WORDS = re.compile(r"[^a-z0-9]+")
_ROMAN = re.compile(r"\s*\((?:[IVXL]+)\)")
_MOVIE = re.compile(r"^(.*?)\s*\((\d{4})")


def key_v2(movie):
    """Title|year key, ignoring IMDb's roman-numeral disambiguators ("Crash (I) (2004)")."""
    if not movie:
        return None
    m = _MOVIE.match(_ROMAN.sub("", movie))
    return movie_key(m.group(1), m.group(2)) if m else None


def shingles(text):
    w = _WORDS.sub(" ", clean_text(text).lower()).split()
    return {zlib.crc32(" ".join(w[j:j + K]).encode()) for j in range(len(w) - K + 1)}


# Near-duplicate index: shingle -> the one val/test review that owns it (shared shingles dropped).
OWNER, SIZE = {}, {}


def build_owner_index():
    for code, split in ((1, "val"), (2, "test")):
        for i, text in enumerate(load_split(split)["text"]):
            rid = code * 100_000 + i
            sh = shingles(text)
            SIZE[rid] = len(sh)
            for s in sh:
                OWNER[s] = -1 if (s in OWNER and OWNER[s] != rid) else rid
    for s in [s for s, r in OWNER.items() if r < 0]:
        del OWNER[s]


def near_dup_share(texts):
    out = np.zeros(len(texts), dtype=np.float32)
    for i, t in enumerate(texts):
        c = Counter(OWNER[s] for s in shingles(t) if s in OWNER)
        if c:
            rid, k = c.most_common(1)[0]
            out[i] = k / max(SIZE[rid], 1)
    return out


def text_batches(path):
    for b in pq.ParquetFile(path).iter_batches(batch_size=20_000, columns=["text"]):
        yield b.column("text").to_pylist()


def length_matched(idx, n_words, labels, target_hist, size, rng):
    """Balanced sample whose word-count histogram matches the official test set."""
    bins = np.clip(np.digitize(n_words[idx], LEN_BINS[1:-1]), 0, len(LEN_BINS) - 2)
    chosen = []
    for label in (0, 1):
        for b, share in enumerate(target_hist):
            cand = idx[(bins == b) & (labels[idx] == label)]
            want = int(round(share * size / 2))
            chosen.append(rng.choice(cand, min(want, len(cand)), replace=False))
    out = np.concatenate(chosen)
    rng.shuffle(out)
    return out


def balanced(idx, labels, rng):
    neg, pos = idx[labels[idx] == 0], idx[labels[idx] == 1]
    n = min(len(neg), len(pos))
    out = np.concatenate([rng.choice(neg, n, replace=False), rng.choice(pos, n, replace=False)])
    rng.shuffle(out)
    return out


def main():
    rng = np.random.default_rng(SEED)
    meta = pq.read_table(POOL / "imdb.parquet", columns=["label", "movie", "reviewer", "n_words"]).to_pandas()
    copies = pq.read_table(POOL / "imdb_split_copies.parquet").to_pandas()
    test_copies = copies[copies["split"] == "test"]
    labels, n_words = meta["label"].to_numpy(), meta["n_words"].to_numpy()

    # 1. reviews of test-set movies
    maas = json.loads((POOL / "maas_movies.json").read_text())
    test_keys = set(maas["test"])
    test_names = set(test_copies["movie"].dropna())
    keys = meta["movie"].map(key_v2)
    test_movie = (keys.isin(test_keys) | meta["movie"].isin(test_names)).to_numpy()
    old_flag = np.load(POOL / "imdb_test_movie_flag.npy")

    # 2. reviews by authors of test reviews
    test_author = meta["reviewer"].isin(set(test_copies["reviewer"].dropna())).to_numpy()

    # 3. near-duplicates of val/test reviews
    build_owner_index()
    with mp.get_context("fork").Pool(6) as workers:
        share = np.concatenate(list(workers.imap(near_dup_share, text_batches(POOL / "imdb.parquet"))))
    near_dup = share >= NEAR_DUP_SHARE
    np.savez(POOL / "imdb_flags_v2.npz", test_movie=test_movie, test_author=test_author,
             near_dup=near_dup, near_dup_share=share)

    # 4. splits_v2
    eligible = ~(test_movie | test_author | near_dup)
    movie_bucket = meta["movie"].fillna("").map(lambda m: zlib.crc32(m.encode()) % VAL_MOVIE_MOD).to_numpy()
    val_movie = movie_bucket == 0
    test_df = load_split("test")
    test_hist = np.bincount(np.clip(np.digitize(test_df["text"].str.split().str.len(), LEN_BINS[1:-1]),
                                    0, len(LEN_BINS) - 2), minlength=len(LEN_BINS) - 1) / len(test_df)
    val_idx = length_matched(np.flatnonzero(eligible & val_movie), n_words, labels, test_hist, VAL_SIZE, rng)
    train_idx = balanced(np.flatnonzero(eligible & ~val_movie), labels, rng)
    defer_idx, chip_idx = train_idx[:DEFER_SIZE], train_idx[DEFER_SIZE:]

    OUT.mkdir(parents=True, exist_ok=True)
    table = pq.read_table(POOL / "imdb.parquet", columns=["text", "label", "source", "n_words", "movie", "reviewer"])
    table = table.set_column(0, "text", pc.cast(table.column("text"), pa.large_string()))
    sets = {"val_pool": val_idx, "defer": defer_idx, "chip_train": chip_idx,
            "test_movie_reviews": np.flatnonzero(test_movie & ~near_dup),
            "test_author_reviews": np.flatnonzero(test_author & ~test_movie & ~near_dup)}
    report = {"pool_rows": int(len(meta)),
              "test_movie": {"rows": int(test_movie.sum()), "previous_flag_rows": int(old_flag.sum()),
                             "newly_flagged": int((test_movie & ~old_flag).sum())},
              "test_author": {"rows": int(test_author.sum()), "authors": int(test_copies["reviewer"].nunique())},
              "near_dup": {f">={t}": int((share >= t).sum()) for t in (0.1, 0.2, 0.3, 0.5, 0.8)},
              "eligible_rows": int(eligible.sum()), "splits": {}}
    for name, idx in sets.items():
        pq.write_table(table.take(np.sort(idx) if name.startswith("test_") else idx), OUT / f"{name}.parquet")
        report["splits"][name] = {"rows": int(len(idx)), "positive_share": float(labels[idx].mean()),
                                  "median_words": int(np.median(n_words[idx]))}
    report["val_pool_movies_disjoint_from_train"] = bool(not (set(meta["movie"].iloc[val_idx]) &
                                                             set(meta["movie"].iloc[train_idx])))
    save_json("pool_hygiene_report.json", report)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
