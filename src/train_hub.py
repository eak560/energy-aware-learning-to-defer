"""Train a large transformer hub on the official train split plus pool reviews.

Built for long runs on hundreds of thousands of reviews:
  - token ids kept as one flat int32 array (not Python lists: ~10x less memory)
  - length-bucketed batches (reviews of similar length together: far less padding)
  - bf16 autocast on Apple GPUs / fp16 on CUDA, gradient accumulation
  - checkpoint every --ckpt-every optimizer steps; rerun the same command to resume
  - val accuracy every --eval-every steps; the best checkpoint is kept

Data: official train (20k) + the first --pool-reviews rows of
data/pool/splits_v2/chip_train.parquet (balanced; movie- and author-disjoint from
the test set; near-duplicates removed; excludes the deferral slice and the
val_pool movies). Never trains on val/test/val_pool. Writes
outputs/{prefix}_{val,val_pool,test,defer}_proba.npy at the end.

    python -I src/train_hub.py --model roberta-base --pool-reviews 300000 --prefix roberta_base_300k
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import torch  # noqa: E402
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,  # noqa: E402
                          get_linear_schedule_with_warmup)
from transformers.utils import logging as hf_logging  # noqa: E402

from common import MODELS_DIR, ROOT, SEED, load_split, metrics, save_json, save_proba  # noqa: E402
from train_transformer import pick_device, special_token_wrap  # noqa: E402

hf_logging.set_verbosity_error()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="roberta-base")
    p.add_argument("--pool-reviews", type=int, default=300_000)
    p.add_argument("--prefix", required=True)
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--max-len", type=int, default=512)
    p.add_argument("--head", type=int, default=128)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--accum", type=int, default=4, help="gradient accumulation steps")
    p.add_argument("--precision", default="bf16", choices=["bf16", "fp16", "fp32"])
    p.add_argument("--eval-every", type=int, default=2000, help="optimizer steps")
    p.add_argument("--ckpt-every", type=int, default=1000, help="optimizer steps")
    p.add_argument("--select-on", default="val_pool", choices=["val_pool", "val"],
                   help="split for picking the best checkpoint (val_pool: 50k, movie-disjoint)")
    p.add_argument("--tokenize-only", action="store_true", help="cache tokens and exit (run on a CPU machine)")
    p.add_argument("--skip-defer", action="store_true", help="skip predicting the 300k deferral slice (saves GPU time)")
    return p.parse_args()


# ---------------------------------------------------------------- tokenised data as flat arrays

class Tokens:
    """Ragged token-id store: one flat int32 array plus offsets."""

    def __init__(self, ids: np.ndarray, offsets: np.ndarray):
        self.ids, self.offsets = ids, offsets

    def __len__(self):
        return len(self.offsets) - 1

    def lengths(self):
        return np.diff(self.offsets)

    def get(self, i):
        return self.ids[self.offsets[i]:self.offsets[i + 1]]

    def save(self, path):
        np.savez(path, ids=self.ids, offsets=self.offsets)

    @classmethod
    def load(cls, path):
        z = np.load(path)
        return cls(z["ids"], z["offsets"])


def tokenize(tokenizer, texts, max_len, head, block=20_000) -> Tokens:
    prefix, suffix = special_token_wrap(tokenizer)
    budget = max_len - len(prefix) - len(suffix)
    tail = budget - head
    chunks, lengths = [], []
    for s in range(0, len(texts), block):
        for seq in tokenizer(texts[s:s + block], add_special_tokens=False, truncation=False)["input_ids"]:
            if len(seq) > budget:
                seq = seq[:head] + seq[len(seq) - tail:]
            seq = prefix + seq + suffix
            chunks.append(np.asarray(seq, dtype=np.int32))
            lengths.append(len(seq))
    offsets = np.zeros(len(lengths) + 1, dtype=np.int64)
    np.cumsum(lengths, out=offsets[1:])
    return Tokens(np.concatenate(chunks), offsets)


def cached_tokens(cache_dir, name, tokenizer, texts_fn, max_len, head) -> Tokens:
    path = cache_dir / f"{name}.npz"
    if path.exists():
        return Tokens.load(path)
    t0 = time.perf_counter()
    tok = tokenize(tokenizer, texts_fn(), max_len, head)
    tok.save(path)
    print(f"tokenised {name}: {len(tok):,} reviews in {time.perf_counter() - t0:.0f}s", flush=True)
    return tok


LOG_EVERY = 20      # optimizer steps between progress lines
PAD_MULTIPLE = 64  # Apple GPUs compile a graph per input shape: few widths = few compiles


def pad_batch(tokens: Tokens, rows, pad_id):
    seqs = [tokens.get(i) for i in rows]
    width = -(-max(len(s) for s in seqs) // PAD_MULTIPLE) * PAD_MULTIPLE
    ids = np.full((len(seqs), width), pad_id, dtype=np.int64)
    mask = np.zeros((len(seqs), width), dtype=np.int64)
    for j, s in enumerate(seqs):
        ids[j, :len(s)] = s
        mask[j, :len(s)] = 1
    return torch.from_numpy(ids), torch.from_numpy(mask)


def bucketed_batches(lengths, batch_size, rng, bucket=100):
    """Shuffle, then sort within windows of `bucket` batches so each batch has similar lengths."""
    order = rng.permutation(len(lengths))
    window = batch_size * bucket
    batches = []
    for s in range(0, len(order), window):
        w = order[s:s + window]
        w = w[np.argsort(lengths[w], kind="stable")]
        batches.extend(w[i:i + batch_size] for i in range(0, len(w), batch_size))
    rng.shuffle(batches)
    return batches


# ---------------------------------------------------------------- train / predict

def autocast(device, precision):
    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16}.get(precision)
    return torch.autocast(device.type, dtype=dtype or torch.float32, enabled=dtype is not None)


@torch.no_grad()
def predict(model, tokens, pad_id, device, precision, batch_size=32):
    model.eval()
    order = np.argsort(tokens.lengths())
    out = np.empty(len(tokens), dtype=np.float32)
    for s in range(0, len(order), batch_size):
        rows = order[s:s + batch_size]
        ids, mask = pad_batch(tokens, rows, pad_id)
        with autocast(device, precision):
            logits = model(input_ids=ids.to(device), attention_mask=mask.to(device)).logits
        out[rows] = torch.softmax(logits.float(), -1)[:, 1].cpu().numpy()
    model.train()
    return out


def main():
    args = parse_args()
    torch.manual_seed(SEED)
    device = pick_device("auto")
    run_dir = MODELS_DIR / args.prefix
    run_dir.mkdir(parents=True, exist_ok=True)
    tok_dir = ROOT / "data" / "cache" / f"tokens_{args.model.replace('/', '_')}_{args.max_len}_{args.head}"
    tok_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    pool_path = ROOT / "data" / "pool" / "splits_v2" / "chip_train.parquet"

    def pool_texts():
        t = pq.read_table(pool_path, columns=["text"]).slice(0, args.pool_reviews)
        return t.column("text").to_pylist()

    def pool_labels():
        return pq.read_table(pool_path, columns=["label"]).slice(0, args.pool_reviews).column("label").to_numpy()

    splits = {s: load_split(s) for s in ("train", "val", "test")}
    tok = {s: cached_tokens(tok_dir, s, tokenizer, lambda s=s: splits[s]["text"].tolist(), args.max_len, args.head)
           for s in splits}
    y_train = splits["train"]["label"].to_numpy().astype(np.int64)
    train_tok = tok["train"]
    if args.pool_reviews > 0:
        # Training set = official train + pool, as one Tokens store.
        tok["pool"] = cached_tokens(tok_dir, f"pool_{args.pool_reviews}", tokenizer, pool_texts, args.max_len, args.head)
        train_tok = Tokens(np.concatenate([tok["train"].ids, tok["pool"].ids]),
                           np.concatenate([tok["train"].offsets[:-1],
                                           tok["pool"].offsets + tok["train"].offsets[-1]]))
        y_train = np.concatenate([y_train, pool_labels()]).astype(np.int64)
    v2 = ROOT / "data" / "pool" / "splits_v2"
    extra = {name: pq.read_table(v2 / f"{name}.parquet", columns=["text", "label"]) for name in ("val_pool", "defer")}
    for name, table in extra.items():
        tok[name] = cached_tokens(tok_dir, f"{name}_v2", tokenizer,
                                  lambda t=table: t.column("text").to_pylist(), args.max_len, args.head)
    if args.tokenize_only:
        print("tokens cached", flush=True)
        return
    label_of = lambda s: splits[s]["label"].to_numpy() if s in splits else extra[s].column("label").to_numpy()
    y_select = label_of(args.select_on)
    lengths = train_tok.lengths()
    print(f"training on {len(train_tok):,} reviews, mean {lengths.mean():.0f} tokens", flush=True)

    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2, dtype=torch.float32).to(device)
    no_decay = ("bias", "LayerNorm.weight", "layernorm", "layer_norm")
    groups = [{"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)], "weight_decay": 0.01},
              {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)], "weight_decay": 0.0}]
    opt = torch.optim.AdamW(groups, lr=args.lr)
    rng = np.random.default_rng(SEED)
    batches = []
    for _ in range(math.ceil(args.epochs)):
        batches.extend(bucketed_batches(lengths, args.batch_size, rng))
    batches = batches[:int(len(batches) * args.epochs / math.ceil(args.epochs))]
    total_steps = len(batches) // args.accum
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * total_steps), total_steps)

    state = {"step": 0, "micro": 0, "best_val": 0.0, "history": []}
    ckpt = run_dir / "checkpoint.pt"
    if ckpt.exists():
        saved = torch.load(ckpt, map_location="cpu", weights_only=False)
        model.load_state_dict(saved["model"])
        opt.load_state_dict(saved["opt"])
        sched.load_state_dict(saved["sched"])
        state = saved["state"]
        print(f"resumed at optimizer step {state['step']:,} / {total_steps:,}", flush=True)

    def save_ckpt():
        tmp = run_dir / "checkpoint.tmp"
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "state": state}, tmp)
        tmp.replace(ckpt)

    model.train()
    t0, running = time.perf_counter(), 0.0
    for b in range(state["micro"], len(batches)):
        ids, mask = pad_batch(train_tok, batches[b], tokenizer.pad_token_id)
        labels = torch.from_numpy(y_train[batches[b]])
        with autocast(device, args.precision):
            loss = model(input_ids=ids.to(device), attention_mask=mask.to(device), labels=labels.to(device)).loss
        (loss / args.accum).backward()
        running += loss.detach()  # summed on the GPU; .item() here would stall every micro-batch
        state["micro"] = b + 1
        if (b + 1) % args.accum:
            continue
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        state["step"] += 1
        step = state["step"]
        if step % LOG_EVERY == 0:
            rate = LOG_EVERY * args.accum * args.batch_size / (time.perf_counter() - t0)
            print(f"step {step:,}/{total_steps:,}  loss {float(running) / (LOG_EVERY * args.accum):.4f}  {rate:.1f} reviews/s", flush=True)
            t0, running = time.perf_counter(), 0.0
        if step % args.eval_every == 0 or step == total_steps:
            p_sel = predict(model, tok[args.select_on], tokenizer.pad_token_id, device, args.precision)
            acc = metrics(y_select, p_sel >= 0.5)["accuracy"]
            state["history"].append({"step": step, f"{args.select_on}_accuracy": acc})
            print(f"  {args.select_on} accuracy {acc:.4f} at step {step:,}", flush=True)
            if acc > state["best_val"]:
                state["best_val"] = acc
                model.save_pretrained(run_dir / "best")
                tokenizer.save_pretrained(run_dir / "best")
            t0 = time.perf_counter()
        if step % args.ckpt_every == 0:
            save_ckpt()
    save_ckpt()

    # Final predictions from the best checkpoint (chosen on --select-on).
    best = AutoModelForSequenceClassification.from_pretrained(run_dir / "best", dtype=torch.float32).to(device)
    report = {"args": vars(args), "train_reviews": len(train_tok), "best_val": state["best_val"], "history": state["history"]}
    for s in ("val", "val_pool", "test") + (() if args.skip_defer else ("defer",)):
        p = predict(best, tok[s], tokenizer.pad_token_id, device, args.precision)
        save_proba(args.prefix, s, p)
        report[s] = metrics(label_of(s), p >= 0.5)
    save_json(f"{args.prefix}_metrics.json", report)
    print(json.dumps({k: report[k] for k in ("best_val", "val", "val_pool", "test")}), flush=True)


if __name__ == "__main__":
    main()
