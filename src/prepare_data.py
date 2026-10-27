"""Download IMDb and write the three splits used by every other script.

    train: 20k reviews (from IMDb's train set) - fit models here
    val:    5k reviews (from IMDb's train set) - pick thresholds and fit the stacker here
    test:  25k reviews (IMDb's test set)      - touched once, for the final numbers
"""

from datasets import load_dataset
from sklearn.model_selection import train_test_split

from common import SEED, SPLITS_DIR, clean_text


def to_frame(split):
    df = split.to_pandas()[["text", "label"]]
    df["text"] = df["text"].map(clean_text)
    return df


def main():
    ds = load_dataset("stanfordnlp/imdb")
    full_train = to_frame(ds["train"])
    test = to_frame(ds["test"])

    # Stratify so both splits keep IMDb's 50/50 positive/negative balance.
    train, val = train_test_split(
        full_train, test_size=5000, stratify=full_train["label"], random_state=SEED
    )

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in [("train", train), ("val", val), ("test", test)]:
        df = df.reset_index(drop=True)
        df.to_parquet(SPLITS_DIR / f"{name}.parquet", index=False)
        print(f"{name:5s}: {len(df):6,d} reviews, {df['label'].mean():.1%} positive")


if __name__ == "__main__":
    main()
