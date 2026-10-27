"""Shared paths, data loading and metrics for the cascade sentiment project."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = ROOT / "data" / "splits"
OUT_DIR = ROOT / "outputs"
MODELS_DIR = OUT_DIR / "models"

SEED = 42
SPLITS = ("train", "val", "test")

_BR_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Replace the <br /> tags IMDb reviews are full of with spaces.

    Casing and punctuation are kept: the transformer uses them, and the
    TF-IDF model lowercases on its own.
    """
    return _BR_TAG.sub(" ", text)


def load_split(name: str) -> pd.DataFrame:
    """Load one split as a DataFrame with `text` and `label` (1 = positive)."""
    path = SPLITS_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python src/prepare_data.py` first.")
    return pd.read_parquet(path)


def metrics(y_true, y_pred) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
    }


def save_proba(prefix: str, split: str, proba: np.ndarray) -> Path:
    """Save P(positive) for every review in a split, e.g. outputs/fast_val_proba.npy."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{prefix}_{split}_proba.npy"
    np.save(path, proba.astype(np.float32))
    return path


def load_proba(prefix: str, split: str) -> np.ndarray:
    path = OUT_DIR / f"{prefix}_{split}_proba.npy"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the {prefix} model script first.")
    return np.load(path)


def save_json(name: str, obj: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(obj, indent=2))
    return path
