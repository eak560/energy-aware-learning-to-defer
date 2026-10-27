"""Which movies are in the official IMDb train / test sets?

Maas et al. (2011) put each movie's reviews entirely in train or entirely in
test, so a model can't score well just by learning which movies people
liked. The Kaggle scrape contains other reviews of those same test movies,
so we flag them. Training scripts can then exclude them, or measure how
much they inflate test accuracy.

Inputs: the urls_*.txt files from the original aclImdb archive (IMDb title
IDs) and IMDb's title.basics.tsv.gz (ID -> title and year). Output:
data/pool/maas_movies.json with normalised "title|year" keys per split.

    python -I src/maas_movies.py --acl data/raw/acl_imdb/aclImdb \
        --titles data/raw/imdb_titles/title.basics.tsv.gz
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from common import ROOT  # noqa: E402

OUT = ROOT / "data" / "pool" / "maas_movies.json"
_TT = re.compile(r"(tt\d+)")
_MOVIE = re.compile(r"^(.*?)\s*\((\d{4})")  # "Kill Bill: Vol. 2 (2004)", "Show (1968– )"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def movie_key(title: str, year) -> str:
    return f"{_NON_ALNUM.sub('', str(title).lower())}|{year}"


def key_from_pool_movie(movie: str):
    """Normalised key for a Kaggle `movie` string, or None if it has no year."""
    if not movie:
        return None
    m = _MOVIE.match(movie)
    return movie_key(m.group(1), m.group(2)) if m else None


def title_ids(acl_dir: Path, split: str) -> set:
    ids = set()
    for name in ("urls_pos.txt", "urls_neg.txt"):
        for line in (acl_dir / split / name).read_text().splitlines():
            m = _TT.search(line)
            if m:
                ids.add(m.group(1))
    return ids


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--acl", type=Path, required=True)
    p.add_argument("--titles", type=Path, required=True)
    args = p.parse_args()

    ids = {split: title_ids(args.acl, split) for split in ("train", "test")}
    wanted = ids["train"] | ids["test"]
    titles = pd.read_csv(args.titles, sep="\t", usecols=["tconst", "primaryTitle", "originalTitle", "startYear"],
                         dtype=str, na_values="\\N", quoting=3)
    titles = titles[titles["tconst"].isin(wanted)]

    out = {"overlap_ids": sorted(ids["train"] & ids["test"])}
    for split, split_ids in ids.items():
        rows = titles[titles["tconst"].isin(split_ids)]
        keys = set()
        for t in rows.itertuples():
            for name in {t.primaryTitle, t.originalTitle}:
                if isinstance(name, str) and isinstance(t.startYear, str):
                    keys.add(movie_key(name, t.startYear))
        out[split] = sorted(keys)
        out[f"{split}_ids"] = len(split_ids)
        out[f"{split}_ids_found_in_title_list"] = int(rows["tconst"].nunique())
        print(f"{split}: {len(split_ids):,} movies, {rows['tconst'].nunique():,} found in IMDb title list, "
              f"{len(keys):,} title keys")
    print(f"movies in both train and test: {len(out['overlap_ids'])}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out))

    # Flag every IMDb pool review that is about an official test-set movie
    # (same row order as data/pool/imdb.parquet).
    pool = OUT.parent / "imdb.parquet"
    if pool.exists():
        test_keys = set(out["test"])
        movies = pq.read_table(pool, columns=["movie"]).column("movie").to_pylist()
        flags = np.fromiter((key_from_pool_movie(m) in test_keys for m in movies), bool, len(movies))
        np.save(OUT.parent / "imdb_test_movie_flag.npy", flags)
        print(f"pool reviews of test-set movies: {flags.sum():,} of {len(flags):,} ({flags.mean():.1%})")


if __name__ == "__main__":
    main()
