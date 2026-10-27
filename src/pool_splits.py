"""Split the clean IMDb pool into the slices later phases need.

    chip_train  balanced, for training the on-device model (Phase 2)
    defer       balanced 300k held out from chip training; the hub labels these
                for the deferral model (Phases 4-5), so neither model has seen them
    test_movies reviews of official test-set movies, kept aside for the
                leakage ablation (does training on them inflate test accuracy?)
    amazon_long balanced Amazon reviews with >= 50 words, for the extra-data ablation

The official IMDb val/test splits stay untouched.

    python -I src/pool_splits.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from common import ROOT, SEED, save_json  # noqa: E402

POOL = ROOT / "data" / "pool"
OUT = POOL / "splits"
DEFER_SIZE = 300_000
AMAZON_MIN_WORDS = 50


def read_pool(path: Path) -> pa.Table:
    # 64-bit string offsets: gathering ~2M reviews overflows Arrow's default 2 GB string limit.
    table = pq.read_table(path)
    i = table.schema.get_field_index("text")
    return table.set_column(i, "text", pc.cast(table.column("text"), pa.large_string()))


def balanced_indices(labels: np.ndarray, rng, per_class=None) -> np.ndarray:
    neg, pos = np.flatnonzero(labels == 0), np.flatnonzero(labels == 1)
    n = min(len(neg), len(pos)) if per_class is None else per_class
    idx = np.concatenate([rng.choice(neg, n, replace=False), rng.choice(pos, n, replace=False)])
    rng.shuffle(idx)
    return idx


def write(table: pa.Table, name: str) -> dict:
    pq.write_table(table.select(["text", "label", "source", "n_words"]), OUT / f"{name}.parquet")
    labels = table.column("label").to_numpy()
    return {"rows": table.num_rows, "positive_share": float(labels.mean())}


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}

    imdb = read_pool(POOL / "imdb.parquet")
    test_movie = np.load(POOL / "imdb_test_movie_flag.npy")
    assert len(test_movie) == imdb.num_rows, "flag file is out of date; rerun the flag step"
    labels = imdb.column("label").to_numpy()

    clean = np.flatnonzero(~test_movie)
    bal = clean[balanced_indices(labels[clean], rng)]
    defer_idx, chip_idx = bal[:DEFER_SIZE], bal[DEFER_SIZE:]
    report["chip_train"] = write(imdb.take(chip_idx), "chip_train")
    report["defer"] = write(imdb.take(defer_idx), "defer")
    report["test_movies"] = write(imdb.take(np.flatnonzero(test_movie)), "test_movies")
    del imdb

    amazon = read_pool(POOL / "amazon.parquet")
    long_rows = np.flatnonzero(amazon.column("n_words").to_numpy() >= AMAZON_MIN_WORDS)
    a_labels = amazon.column("label").to_numpy()[long_rows]
    report["amazon_long"] = write(amazon.take(long_rows[balanced_indices(a_labels, rng)]), "amazon_long")

    save_json("pool_splits_report.json", report)
    for name, r in report.items():
        print(f"{name:12s} {r['rows']:>10,} rows  {r['positive_share']:.1%} positive")


if __name__ == "__main__":
    main()
