"""Predict with a trained hub, reading long reviews in full.

Training truncates reviews over 512 tokens to head 128 + tail 382. At
prediction time this script also slides 510-token windows (stride 255) over
the whole review and averages the logits of every window plus the usual
head+tail view, so nothing in a long review is ignored. Short reviews are
unchanged. Whether it helps is decided on val_pool, never on test.

Writes outputs/{prefix}_chunked_{val,val_pool,test}_proba.npy and
outputs/{prefix}_chunked_metrics.json.

    python -I src/predict_hub.py --prefix roberta_large_1m
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
from transformers.utils import logging as hf_logging  # noqa: E402

from common import MODELS_DIR, ROOT, load_split, metrics, save_json, save_proba  # noqa: E402
from train_hub import PAD_MULTIPLE, autocast  # noqa: E402
from train_transformer import pick_device, special_token_wrap  # noqa: E402

hf_logging.set_verbosity_error()


def windows(ids, budget, head, stride):
    """All views of one review: head+tail, plus sliding windows if it is long."""
    if len(ids) <= budget:
        return [ids]
    views = [ids[:head] + ids[len(ids) - (budget - head):]]
    starts = list(range(0, len(ids) - budget + 1, stride))
    if starts[-1] != len(ids) - budget:
        starts.append(len(ids) - budget)
    views.extend(ids[s:s + budget] for s in starts)
    return views


@torch.no_grad()
def predict_long(model, tokenizer, texts, device, precision, max_len=512, head=128, stride=255, batch_size=64):
    prefix, suffix = special_token_wrap(tokenizer)
    budget = max_len - len(prefix) - len(suffix)
    all_ids = tokenizer(texts, add_special_tokens=False, truncation=False)["input_ids"]
    views, owner = [], []
    for i, ids in enumerate(all_ids):
        for v in windows(ids, budget, head, stride):
            views.append(prefix + v + suffix)
            owner.append(i)
    owner = np.asarray(owner)
    order = np.argsort([len(v) for v in views])
    logits = np.zeros((len(views), 2), dtype=np.float32)
    model.eval()
    for s in range(0, len(order), batch_size):
        rows = order[s:s + batch_size]
        width = -(-max(len(views[r]) for r in rows) // PAD_MULTIPLE) * PAD_MULTIPLE
        ids = np.full((len(rows), width), tokenizer.pad_token_id, dtype=np.int64)
        mask = np.zeros_like(ids)
        for j, r in enumerate(rows):
            ids[j, :len(views[r])] = views[r]
            mask[j, :len(views[r])] = 1
        with autocast(device, precision):
            out = model(input_ids=torch.from_numpy(ids).to(device), attention_mask=torch.from_numpy(mask).to(device))
        logits[rows] = out.logits.float().cpu().numpy()
    mean_logits = np.zeros((len(texts), 2), dtype=np.float64)
    np.add.at(mean_logits, owner, logits)
    mean_logits /= np.bincount(owner, minlength=len(texts))[:, None]
    z = mean_logits[:, 1] - mean_logits[:, 0]
    return (1 / (1 + np.exp(-z))).astype(np.float32), float(np.mean([len(x) > budget for x in all_ids]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True)
    p.add_argument("--precision", default="bf16")
    args = p.parse_args()

    device = pick_device("auto")
    model_dir = MODELS_DIR / args.prefix / "best"
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, dtype=torch.float32).to(device)
    data = {s: load_split(s) for s in ("val", "test")}
    vp = pq.read_table(ROOT / "data" / "pool" / "splits_v2" / "val_pool.parquet", columns=["text", "label"])
    data["val_pool"] = vp.to_pandas()

    report = {}
    for split in ("val", "val_pool", "test"):
        proba, long_share = predict_long(model, tokenizer, data[split]["text"].tolist(), device, args.precision)
        save_proba(f"{args.prefix}_chunked", split, proba)
        report[split] = {**metrics(data[split]["label"].to_numpy(), proba >= 0.5), "long_review_share": long_share}
        print(split, report[split], flush=True)
    save_json(f"{args.prefix}_chunked_metrics.json", report)


if __name__ == "__main__":
    main()
