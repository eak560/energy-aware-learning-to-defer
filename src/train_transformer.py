"""Stage 2 of the cascade: fine-tune DistilBERT on the train split.

Long reviews use head+tail truncation (first 128 + last 382 tokens) rather
than keeping only the first 512, because reviewers often put the verdict at
the end (Sun et al., 2019). Saves P(positive) for val and test to
outputs/{prefix}_{split}_proba.npy and the fine-tuned model to outputs/models/.

    python src/train_transformer.py                 # full run (cuda > mps > cpu)
    python src/train_transformer.py --limit 200     # quick smoke test
"""

import argparse
import random
import time

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm.auto import tqdm
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)
from transformers.utils import logging as hf_logging

from common import MODELS_DIR, SEED, load_split, metrics, save_json, save_proba

hf_logging.set_verbosity_error()  # silences "sequence longer than 512" - we truncate ourselves


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="distilbert-base-uncased")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-5)
    p.add_argument("--max-len", type=int, default=512)
    p.add_argument("--head", type=int, default=128, help="tokens kept from the start of long reviews")
    p.add_argument("--device", default="auto", help="auto, cuda, mps or cpu")
    p.add_argument("--limit", type=int, default=None, help="use only N reviews per split (smoke test)")
    p.add_argument("--prefix", default="bert", help="name used for the saved prediction files")
    return p.parse_args()


def pick_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def special_token_wrap(tokenizer):
    """The ids the tokenizer puts before and after a single text, e.g.
    ([CLS], [SEP]) for BERT or (<s>, </s>) for RoBERTa, found by encoding one
    word with and without special tokens."""
    bare = tokenizer("a", add_special_tokens=False)["input_ids"]
    full = tokenizer("a")["input_ids"]
    i = next(i for i in range(len(full)) if full[i:i + len(bare)] == bare)
    return full[:i], full[i + len(bare):]


def encode_head_tail(tokenizer, texts, max_len: int, head: int):
    """Tokenise without truncation, then keep the first `head` and the last
    `budget - head` tokens of any review longer than the budget."""
    prefix, suffix = special_token_wrap(tokenizer)
    budget = max_len - len(prefix) - len(suffix)  # 510 for [CLS] ... [SEP]
    tail = budget - head
    ids = tokenizer(list(texts), add_special_tokens=False, truncation=False)["input_ids"]
    encoded, n_truncated = [], 0
    for seq in ids:
        if len(seq) > budget:
            seq = seq[:head] + seq[len(seq) - tail:]
            n_truncated += 1
        encoded.append(prefix + seq + suffix)
    return encoded, n_truncated / len(ids)


class PadCollator:
    """Pads each batch only to its own longest review (dynamic padding)."""

    def __init__(self, pad_id: int):
        self.pad_id = pad_id

    def __call__(self, batch):
        width = max(len(ids) for ids, _ in batch)
        input_ids = torch.full((len(batch), width), self.pad_id, dtype=torch.long)
        attention_mask = torch.zeros((len(batch), width), dtype=torch.long)
        for i, (ids, _) in enumerate(batch):
            input_ids[i, :len(ids)] = torch.tensor(ids)
            attention_mask[i, :len(ids)] = 1
        labels = torch.tensor([label for _, label in batch], dtype=torch.long)
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def sync(device: torch.device):
    if device.type == "cuda":
        torch.cuda.synchronize()
    elif device.type == "mps":
        torch.mps.synchronize()


@torch.no_grad()
def predict_proba(model, encoded, collate, batch_size, device, desc="predict"):
    """P(positive) for every encoded review. Batches are built from
    length-sorted reviews so short reviews aren't padded out to 512."""
    model.eval()
    order = np.argsort([len(ids) for ids in encoded])
    proba = np.empty(len(encoded), dtype=np.float32)
    for start in tqdm(range(0, len(order), batch_size), desc=desc, mininterval=10):
        idx = order[start:start + batch_size]
        batch = collate([(encoded[i], 0) for i in idx])
        with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
            logits = model(input_ids=batch["input_ids"].to(device),
                           attention_mask=batch["attention_mask"].to(device)).logits
        proba[idx] = torch.softmax(logits.float(), dim=-1)[:, 1].cpu().numpy()
    sync(device)
    model.train()
    return proba


def main():
    args = parse_args()
    seed_everything(SEED)
    device = pick_device(args.device)
    print(f"device: {device}")

    splits = {name: load_split(name) for name in ("train", "val", "test")}
    if args.limit:
        splits = {name: df.sample(n=min(args.limit, len(df)), random_state=SEED).reset_index(drop=True)
                  for name, df in splits.items()}

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    encoded, truncated_share = {}, {}
    for name, df in splits.items():
        encoded[name], truncated_share[name] = encode_head_tail(tokenizer, df["text"], args.max_len, args.head)
        print(f"{name:5s}: {len(df):6,d} reviews, {truncated_share[name]:.1%} longer than {args.max_len} tokens")

    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2, dtype=torch.float32).to(device)
    collate = PadCollator(tokenizer.pad_token_id)
    train_data = list(zip(encoded["train"], splits["train"]["label"].tolist()))
    loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, collate_fn=collate,
                        generator=torch.Generator().manual_seed(SEED))

    # Standard BERT fine-tuning recipe: AdamW, no weight decay on biases/LayerNorm,
    # linear warmup over the first 6% of steps then linear decay to zero.
    no_decay = ("bias", "LayerNorm.weight")
    param_groups = [
        {"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)], "weight_decay": 0.01},
        {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)], "weight_decay": 0.0},
    ]
    optimizer = torch.optim.AdamW(param_groups, lr=args.lr)
    total_steps = len(loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.06 * total_steps), total_steps)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    history = []
    t_train = time.perf_counter()
    model.train()
    for epoch in range(1, args.epochs + 1):
        running = 0.0
        bar = tqdm(loader, desc=f"epoch {epoch}/{args.epochs}", mininterval=10)
        for step, batch in enumerate(bar, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                loss = model(**batch).loss
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            running += loss.item()
            if step % 50 == 0:
                bar.set_postfix(loss=f"{running / step:.4f}")

        p_val = predict_proba(model, encoded["val"], collate, args.batch_size * 2, device, desc="val")
        val_m = metrics(splits["val"]["label"], p_val >= 0.5)
        history.append({"epoch": epoch, "train_loss": running / len(loader), **{f"val_{k}": v for k, v in val_m.items()}})
        print(f"epoch {epoch}: train loss {running / len(loader):.4f}  val accuracy {val_m['accuracy']:.4f}  f1 {val_m['f1']:.4f}")
    train_seconds = time.perf_counter() - t_train

    t0 = time.perf_counter()
    p_test = predict_proba(model, encoded["test"], collate, args.batch_size * 2, device, desc="test")
    test_seconds = time.perf_counter() - t0

    save_proba(args.prefix, "val", p_val)
    save_proba(args.prefix, "test", p_test)
    if not args.limit:
        out = MODELS_DIR / "distilbert-imdb"
        model.save_pretrained(out)
        tokenizer.save_pretrained(out)

    report = {
        "args": vars(args),
        "device": str(device),
        "truncated_share": truncated_share,
        "history": history,
        "val": metrics(splits["val"]["label"], p_val >= 0.5),
        "test": metrics(splits["test"]["label"], p_test >= 0.5),
        "test_reviews_per_sec": len(p_test) / test_seconds,
        "train_seconds": train_seconds,
    }
    save_json(f"{args.prefix}_metrics.json", report)
    print(f"test accuracy {report['test']['accuracy']:.4f}  f1 {report['test']['f1']:.4f}")
    print(f"throughput    {report['test_reviews_per_sec']:,.1f} reviews/sec ({device})")


if __name__ == "__main__":
    main()
