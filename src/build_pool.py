"""Phase 1: build a large, leakage-free review pool from the raw downloads.

    IMDb (Kaggle, Biswas): rating <= 4/10 -> negative, >= 7/10 -> positive
    Amazon Movies & TV (HF): 1-2 stars -> negative, 4-5 -> positive
    Middle and missing ratings are dropped. Amazon review titles are dropped
    too: they often state the rating outright ("Five Stars").

Every pool review is compared with our IMDb train/val/test splits after
normalising the text (lowercase, letters and digits only). It is dropped if
it matches a split review exactly, or shares its first or last 200
characters (catches truncated or lightly edited copies). Exact duplicates
inside the pool are dropped too. All counts go to outputs/pool_report.json.

Raw files are untrusted downloads: run with `python -I` and pass paths in.

    python -I src/build_pool.py --imdb data/raw/kaggle_imdb/part-0*.json \
        --amazon data/raw/amazon_movies_tv/Movies_and_TV.jsonl
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import ijson  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from common import ROOT, clean_text, load_split, save_json  # noqa: E402

POOL_DIR = ROOT / "data" / "pool"
EDGE = 200  # characters of normalised text used for prefix/suffix matching
BATCH = 100_000

SCHEMA = pa.schema([
    ("text", pa.string()),
    ("label", pa.int8()),
    ("source", pa.string()),
    ("movie", pa.string()),
    ("rating", pa.float32()),
    ("n_words", pa.int32()),
    ("review_id", pa.string()),
    ("reviewer", pa.string()),
    ("review_date", pa.string()),
])

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    # The Kaggle scrape glues lines together without spaces ("Vol. 2.Hedeen's")
    # while the original has <br /> tags, so drop all whitespace and punctuation.
    return _NON_ALNUM.sub("", clean_text(text).lower())


def h(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")


def fingerprints(norm: str):
    full = h(norm)
    if len(norm) < EDGE * 2:
        return full, None, None
    return full, h(norm[:EDGE]), h(norm[-EDGE:])


def reference_index():
    """Fingerprints of every review in our IMDb splits -> split name."""
    index = {"full": {}, "prefix": {}, "suffix": {}}
    for split in ("train", "val", "test"):
        for text in load_split(split)["text"]:
            full, pre, suf = fingerprints(normalise(text))
            index["full"][full] = split
            if pre is not None:
                index["prefix"][pre] = split
                index["suffix"][suf] = split
    return index


def imdb_rows(paths):
    for path in paths:
        with open(path, "rb") as f:
            for r in ijson.items(f, "item"):
                rating = r.get("rating")
                rating = float(rating) if rating not in (None, "") else None
                row = {"text": r.get("review_detail") or "", "source": "imdb", "movie": r.get("movie"),
                       "rating": rating, "review_id": r.get("review_id"), "reviewer": r.get("reviewer"),
                       "review_date": r.get("review_date")}
                if rating is None or 4 < rating < 7:
                    yield row, "imdb_unlabelled"  # kept out of the pool, but still checked for split copies
                    continue
                row["label"] = int(rating >= 7)
                yield row, None


def amazon_rows(path):
    with open(path, "rb") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                yield None, "amazon_bad_line"  # e.g. a partially downloaded last line
                continue
            rating = r.get("rating")
            if rating is None or rating == 3:
                yield None, "amazon_unlabelled"  # Amazon copies of IMDb reviews are rare; not logged
                continue
            yield {"text": r.get("text") or "", "label": int(rating >= 4), "source": "amazon",
                   "movie": None, "rating": float(rating), "review_id": None, "reviewer": r.get("user_id"),
                   "review_date": None}, None


def match_split(ref, full, pre, suf):
    split, how = ref["full"].get(full), "exact"
    if split is None and pre is not None:
        split, how = ref["prefix"].get(pre), "prefix"
        if split is None:
            split, how = ref["suffix"].get(suf), "suffix"
    return split, how


def build(name, rows, ref, counts, seen):
    """Write the pool, plus <name>_split_copies.parquet: every raw review that copies one of our
    split reviews (labelled or not), with its movie and author, for movie/author-level checks."""
    out = POOL_DIR / f"{name}.parquet"
    writer, batch, copies = pq.ParquetWriter(out, SCHEMA), [], []
    for row, skip in rows:
        counts[f"{name}_read"] += 1
        if skip:
            counts[skip] += 1
            if row is not None:
                norm = normalise(clean_text(row["text"]))
                if len(norm) >= 20:
                    split, how = match_split(ref, *fingerprints(norm))
                    if split is not None:
                        copies.append({**{k: row.get(k) for k in ("movie", "review_id", "reviewer", "rating")},
                                       "split": split, "how": how, "labelled": False})
            continue
        text = clean_text(row["text"]).strip()
        norm = normalise(text)
        if len(norm) < 20:
            counts[f"{name}_too_short"] += 1
            continue
        full, pre, suf = fingerprints(norm)
        if full in seen:
            counts[f"{name}_duplicate_in_pool"] += 1
            continue
        seen.add(full)
        split, how = match_split(ref, full, pre, suf)
        if split is not None:
            counts[f"{name}_matches_{split}_{how}"] += 1
            copies.append({**{k: row.get(k) for k in ("movie", "review_id", "reviewer", "rating")},
                           "split": split, "how": how, "labelled": True})
            continue
        row.update(text=text, n_words=len(text.split()))
        batch.append(row)
        counts[f"{name}_kept"] += 1
        counts[f"{name}_kept_label{row['label']}"] += 1
        if len(batch) >= BATCH:
            writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA))
            batch = []
            print(f"{name}: {counts[f'{name}_kept']:,} kept / {counts[f'{name}_read']:,} read", flush=True)
    if batch:
        writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA))
    writer.close()
    if copies:
        pq.write_table(pa.Table.from_pylist(copies), POOL_DIR / f"{name}_split_copies.parquet")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--imdb", nargs="*", default=[], help="Kaggle IMDb part-*.json files")
    p.add_argument("--amazon", default=None, help="Amazon Movies_and_TV.jsonl")
    p.add_argument("--report", default="pool_report.json")
    args = p.parse_args()

    POOL_DIR.mkdir(parents=True, exist_ok=True)
    ref = reference_index()
    print(f"reference fingerprints: {len(ref['full']):,} full, {len(ref['prefix']):,} prefix", flush=True)
    counts, seen = Counter(), set()
    if args.imdb:
        build("imdb", imdb_rows(args.imdb), ref, counts, seen)
    if args.amazon:
        build("amazon", amazon_rows(args.amazon), ref, counts, seen)
    report = dict(sorted(counts.items()))
    save_json(args.report, report)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
