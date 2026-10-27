"""Phase 4: the hub model's predictions on the held-out deferral slice.

DistilBERT was fine-tuned only on the official 20k train split and the chip
model never trains on this slice, so both models' answers here are honest.
Phase 5 turns them into deferral labels (chip wrong and hub right, etc.).
Reviews go through in blocks so token lists for 300k reviews never sit in
memory at once. Saves outputs/bert_defer_proba.npy.

    python -I src/hub_labels.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

from common import MODELS_DIR, ROOT, save_json, save_proba  # noqa: E402
from train_transformer import PadCollator, encode_head_tail, pick_device, predict_proba  # noqa: E402

BLOCK = 20_000


def main():
    device = pick_device("auto")
    model_dir = MODELS_DIR / "distilbert-imdb"
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, dtype=torch.float32).to(device)
    collate = PadCollator(tokenizer.pad_token_id)

    parts, n, t0 = [], 0, time.perf_counter()
    source = pq.ParquetFile(ROOT / "data" / "pool" / "splits" / "defer.parquet")
    for batch in source.iter_batches(batch_size=BLOCK, columns=["text"]):
        encoded, _ = encode_head_tail(tokenizer, batch.column("text").to_pylist(), 512, 128)
        parts.append(predict_proba(model, encoded, collate, 32, device, desc=f"defer {n:,}"))
        n += len(encoded)
        print(f"{n:,} reviews, {n / (time.perf_counter() - t0):.0f}/s", flush=True)
    proba = np.concatenate(parts)
    save_proba("bert", "defer", proba)
    save_json("hub_labels_report.json", {"reviews": int(n), "seconds": time.perf_counter() - t0, "device": str(device)})


if __name__ == "__main__":
    main()
