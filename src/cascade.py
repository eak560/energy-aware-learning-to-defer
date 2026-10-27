"""Stage 3: combine the two models with a confidence-gated cascade.

1. Sweep the confidence threshold tau on the val split. A review whose
   TF-IDF confidence max(p, 1 - p) is below tau goes to DistilBERT.
2. Pick tau with a rule fixed in advance: the fewest reviews routed while
   staying within --tolerance of DistilBERT-alone accuracy on val.
3. Apply that one tau to the test split, and compare against both models
   alone and a stacked ensemble (an LR fitted on val over both models' outputs).
4. Benchmark real end-to-end throughput on a sample of test reviews.
5. Write review samples and length breakdowns for error analysis.

Needs: outputs/fast_*_proba.npy, outputs/bert_*_proba.npy and both saved models.
Other model pairs: --fast-prefix / --bert-prefix pick the prediction files and
--tag suffixes every output (the benchmark times the saved TF-IDF and
DistilBERT models, so skip it with --benchmark 0 for other pairs):

    python src/cascade.py --fast-prefix ngram256KB --bert-prefix roberta_base_1m --benchmark 0 --tag roberta_base_1m
"""

import argparse
import time

import joblib
import matplotlib
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from common import MODELS_DIR, OUT_DIR, SEED, load_proba, load_split, metrics, save_json
from train_transformer import PadCollator, encode_head_tail, pick_device, predict_proba

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--tolerance", type=float, default=0.005,
                   help="max val accuracy given up versus DistilBERT alone (0.005 = 0.5 points)")
    p.add_argument("--benchmark", type=int, default=2000,
                   help="test reviews to time end to end (0 skips the benchmark)")
    p.add_argument("--fast-prefix", default="fast")
    p.add_argument("--bert-prefix", default="bert")
    p.add_argument("--tag", default="", help="suffix for output files (empty keeps the original names)")
    p.add_argument("--batch-size", type=int, default=32)
    return p.parse_args()


def confidence(p: np.ndarray) -> np.ndarray:
    return np.maximum(p, 1 - p)


def route(p_fast, p_bert, tau):
    """Cascade prediction: keep the fast answer when it's confident, else ask DistilBERT."""
    routed = confidence(p_fast) < tau
    pred = np.where(routed, p_bert >= 0.5, p_fast >= 0.5).astype(int)
    return pred, routed


def sweep(p_fast, p_bert, y):
    # tau = 0.5 routes nothing; confidence never exceeds 1, so tau = 1.0001 routes everything.
    taus = list(np.round(np.linspace(0.5, 1.0, 201), 4)) + [1.0001]
    rows = []
    for tau in taus:
        pred, routed = route(p_fast, p_bert, tau)
        rows.append({"tau": float(tau), "routed": float(routed.mean()), **metrics(y, pred)})
    return rows


def choose_tau(rows, bert_acc, tolerance):
    ok = [r for r in rows if r["accuracy"] >= bert_acc - tolerance]
    return min(ok, key=lambda r: (r["routed"], -r["accuracy"]))


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def stacked_ensemble(pf_val, pb_val, y_val, pf_test, pb_test):
    X_val = np.column_stack([logit(pf_val), logit(pb_val)])
    X_test = np.column_stack([logit(pf_test), logit(pb_test)])
    stacker = LogisticRegression().fit(X_val, y_val)
    return (stacker.predict_proba(X_test)[:, 1] >= 0.5).astype(int), stacker.coef_[0].tolist()


def by_length(df, preds: dict):
    """Accuracy of each model per review-length quartile."""
    words = df["text"].str.split().str.len()
    buckets = pd.qcut(words, 4)
    out = []
    for bucket in buckets.cat.categories:
        mask = (buckets == bucket).to_numpy()
        row = {"words": f"{int(bucket.left) + 1}-{int(bucket.right)}", "n": int(mask.sum())}
        for name, pred in preds.items():
            row[name] = float((pred[mask] == df["label"].to_numpy()[mask]).mean())
        out.append(row)
    return out


def error_samples(df, p_fast, p_bert, routed, n=30):
    y = df["label"].to_numpy()
    fast_ok, bert_ok = (p_fast >= 0.5) == y, (p_bert >= 0.5) == y
    groups = {
        "bert_fixed": ~fast_ok & bert_ok,
        "bert_broke": fast_ok & ~bert_ok,
        "both_wrong": ~fast_ok & ~bert_ok,
    }
    frames = []
    for name, mask in groups.items():
        sub = df[mask].assign(group=name, fast_proba=p_fast[mask], bert_proba=p_bert[mask],
                              routed=routed[mask], words=df["text"][mask].str.split().str.len())
        frames.append(sub.sample(n=min(n, len(sub)), random_state=SEED))
    out = pd.concat(frames)[["group", "label", "fast_proba", "bert_proba", "routed", "words", "text"]]
    out["tag"] = ""  # fill in by hand: negation / sarcasm / long / mixed / label noise ...
    counts = {name: int(mask.sum()) for name, mask in groups.items()}
    return out, counts


def benchmark(test, n, tau, batch_size):
    """Time each system end to end on the same n raw test reviews, including
    vectorising / tokenising, so the speed numbers are comparable."""
    sample = test.sample(n=min(n, len(test)), random_state=SEED).reset_index(drop=True)
    texts = sample["text"].tolist()

    fast = joblib.load(MODELS_DIR / "fast_model.joblib")
    device = pick_device("auto")
    bert_dir = MODELS_DIR / "distilbert-imdb"
    tokenizer = AutoTokenizer.from_pretrained(bert_dir)
    model = AutoModelForSequenceClassification.from_pretrained(bert_dir, dtype=torch.float32).to(device)
    collate = PadCollator(tokenizer.pad_token_id)

    def bert(batch_texts):
        if not batch_texts:
            return np.empty(0, dtype=np.float32)
        enc, _ = encode_head_tail(tokenizer, batch_texts, 512, 128)
        return predict_proba(model, enc, collate, batch_size, device, desc="benchmark")

    bert(texts[:batch_size])  # warm-up: the first GPU call pays one-off kernel setup costs
    fast.predict_proba(texts[:batch_size])

    t0 = time.perf_counter()
    p_fast = fast.predict_proba(texts)[:, 1]
    fast_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    bert(texts)
    bert_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    p = fast.predict_proba(texts)[:, 1]
    routed = confidence(p) < tau
    bert([t for t, r in zip(texts, routed) if r])
    cascade_s = time.perf_counter() - t0

    return {
        "n_reviews": len(texts),
        "device": str(device),
        "routed_share": float(routed.mean()),
        "reviews_per_sec": {
            "fast": len(texts) / fast_s,
            "bert": len(texts) / bert_s,
            "cascade": len(texts) / cascade_s,
            "stacked": len(texts) / (fast_s + bert_s),  # needs both models on every review
        },
        "fast_proba_matches_saved": bool(np.allclose(p_fast, p, atol=1e-6)),
    }


def plot_curve(rows, fast_acc, bert_acc, chosen, path, fast_name="TF-IDF + LR", bert_name="DistilBERT"):
    surface, ink, ink2, grid, blue = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
    x = [r["routed"] * 100 for r in rows]
    y = [r["accuracy"] * 100 for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200, facecolor=surface)
    ax.set_facecolor(surface)
    ax.plot(x, y, color=blue, lw=2, solid_capstyle="round", zorder=2)

    # Reference lines, labelled directly where the curve isn't.
    ax.axhline(bert_acc * 100, color=ink2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(99, bert_acc * 100 - 0.08, f"{bert_name} alone  {bert_acc:.2%}", color=ink2, fontsize=9,
            ha="right", va="top")
    ax.axhline(fast_acc * 100, color=ink2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(99, fast_acc * 100 - 0.08, f"{fast_name} alone  {fast_acc:.2%}", color=ink2, fontsize=9,
            ha="right", va="top")

    cx, cy = chosen["routed"] * 100, chosen["accuracy"] * 100
    ax.plot(cx, cy, "o", ms=9, color=blue, mec=surface, mew=2, zorder=3)
    ax.annotate(f"chosen τ = {chosen['tau']:.3f}\n{chosen['routed']:.0%} routed, {chosen['accuracy']:.2%}",
                xy=(cx, cy), xytext=(14, -34), textcoords="offset points", color=ink, fontsize=9,
                arrowprops={"arrowstyle": "-", "color": ink2, "lw": 0.8})

    ax.set_xlim(0, 100)
    ax.set_ylim(fast_acc * 100 - 0.8, max(y) + 0.6)
    ax.set_xlabel(f"Reviews sent to {bert_name} (%)", color=ink2, fontsize=9.5)
    ax.set_ylabel("Validation accuracy (%)", color=ink2, fontsize=9.5)
    ax.set_title("Cascade accuracy vs. share of reviews routed to the transformer (validation set)",
                 loc="left", color=ink, fontsize=11, pad=12)
    ax.grid(axis="y", color=grid, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(grid)
    ax.tick_params(colors=ink2, labelsize=9, length=0)

    fig.tight_layout()
    fig.savefig(path, facecolor=surface)
    plt.close(fig)


def results_table(rows) -> str:
    lines = ["| Model | Accuracy | F1 | Sent to transformer | Reviews/sec |",
             "|---|---|---|---|---|"]
    for r in rows:
        speed = f"{r['speed']:,.0f}" if r["speed"] is not None else "-"
        lines.append(f"| {r['name']} | {r['accuracy']:.2%} | {r['f1']:.4f} | {r['routed']:.1%} | {speed} |")
    return "\n".join(lines)


def main():
    args = parse_args()
    suffix = f"_{args.tag}" if args.tag else ""
    fast_name = "TF-IDF + LR" if args.fast_prefix == "fast" else args.fast_prefix
    bert_name = "DistilBERT" if args.bert_prefix == "bert" else args.bert_prefix
    val, test = load_split("val"), load_split("test")
    y_val, y_test = val["label"].to_numpy(), test["label"].to_numpy()
    pf_val, pf_test = load_proba(args.fast_prefix, "val"), load_proba(args.fast_prefix, "test")
    pb_val, pb_test = load_proba(args.bert_prefix, "val"), load_proba(args.bert_prefix, "test")
    for name, arr, df in [("fast val", pf_val, val), ("fast test", pf_test, test),
                          ("bert val", pb_val, val), ("bert test", pb_test, test)]:
        assert len(arr) == len(df), f"{name}: {len(arr)} predictions for {len(df)} reviews"

    # 1-2. Choose tau on val only.
    rows = sweep(pf_val, pb_val, y_val)
    fast_val, bert_val = metrics(y_val, pf_val >= 0.5), metrics(y_val, pb_val >= 0.5)
    chosen = choose_tau(rows, bert_val["accuracy"], args.tolerance)
    tau = chosen["tau"]
    print(f"val: fast {fast_val['accuracy']:.4f}  bert {bert_val['accuracy']:.4f}  "
          f"-> tau {tau:.3f} routes {chosen['routed']:.1%} at {chosen['accuracy']:.4f}")

    # 3. Apply the chosen tau to test once.
    cascade_pred, routed = route(pf_test, pb_test, tau)
    stacked_pred, stacker_coef = stacked_ensemble(pf_val, pb_val, y_val, pf_test, pb_test)
    test_results = {
        "fast": metrics(y_test, pf_test >= 0.5),
        "bert": metrics(y_test, pb_test >= 0.5),
        "cascade": {**metrics(y_test, cascade_pred), "routed": float(routed.mean())},
        "stacked": metrics(y_test, stacked_pred),
        # Share of reviews at least one model gets right: the ceiling for any way of combining them.
        "either_correct": float((((pf_test >= 0.5) == y_test) | ((pb_test >= 0.5) == y_test)).mean()),
    }

    # 4. Real throughput.
    bench = benchmark(test, args.benchmark, tau, args.batch_size) if args.benchmark else None
    speed = (bench or {}).get("reviews_per_sec", {})

    # 5. Error analysis material.
    samples, group_counts = error_samples(test, pf_test, pb_test, routed)
    samples.to_csv(OUT_DIR / f"error_analysis{suffix}.csv", index=False)
    length_table = by_length(test, {"fast": (pf_test >= 0.5).astype(int),
                                    "bert": (pb_test >= 0.5).astype(int),
                                    "cascade": cascade_pred})

    table = results_table([
        {"name": fast_name, **test_results["fast"], "routed": 0.0, "speed": speed.get("fast")},
        {"name": bert_name, **test_results["bert"], "routed": 1.0, "speed": speed.get("bert")},
        {"name": f"**Cascade** (τ = {tau:.3f})", **test_results["cascade"], "speed": speed.get("cascade")},
        {"name": "Stacked ensemble (upper bound)", **test_results["stacked"], "routed": 1.0,
         "speed": speed.get("stacked")},
    ])
    (OUT_DIR / f"results_table{suffix}.md").write_text(table + "\n")
    plot_curve(rows, fast_val["accuracy"], bert_val["accuracy"], chosen, OUT_DIR / f"cascade_curve{suffix}.png",
               fast_name, bert_name)

    save_json(f"cascade_results{suffix}.json", {
        "fast_prefix": args.fast_prefix, "bert_prefix": args.bert_prefix,
        "selection_rule": f"fewest routed with val accuracy >= DistilBERT val accuracy - {args.tolerance}",
        "tau": tau,
        "val": {"fast": fast_val, "bert": bert_val, "cascade_at_tau": chosen,
                "most_accurate_tau": max(rows, key=lambda r: (r["accuracy"], -r["routed"]))},
        "test": test_results,
        "stacker_coef": {"fast_logit": stacker_coef[0], "bert_logit": stacker_coef[1]},
        "benchmark": bench,
        "error_group_counts": group_counts,
        "accuracy_by_length": length_table,
        "val_sweep": rows,
    })

    print()
    print(table)
    print(f"\nat least one model right on {test_results['either_correct']:.2%} of test reviews")
    print("errors:", group_counts)
    print("\naccuracy by review length (words):")
    print(pd.DataFrame(length_table).to_string(index=False, float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    main()
