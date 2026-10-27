"""Phase 5: learning to defer.

For every review in the held-out deferral slice we know what each model got
right, so the gain from sending it to the hub is

    gain = hub_right - chip_right   (+1 the hub fixes it, 0 no change, -1 the hub breaks it)

A small deferral model learns to predict that gain from things the chip can
compute: 2^16 hashed n-gram buckets, the chip's own confidence (binned) and
the review's length (number of distinct n-grams, binned). The device sends a
review when g(x) = P(fix) - P(break) is above a threshold.

Compared on the official test split against:
  confidence routing  send the reviews the chip is least sure about
  oracle              send exactly the reviews the hub fixes (impossible upper bound)
Curves pick thresholds by send rate, which needs no labels. Headline
operating points pick their threshold on the val split, including a
"val_best" point: the send rate with the highest val accuracy.

    python -I src/defer_router.py
    # retrained hub (Phase 5 follow-up): v2 chip, v2 deferral slice, 1M-review hub
    python -I src/defer_router.py --chip-prefix ngram256KB --defer-cache defer_v2 \
        --hub-prefix roberta_base_1m --tag roberta_base_1m
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
from scipy.stats import binomtest  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.preprocessing import normalize  # noqa: E402

from chip_model import CACHE, binary_csr, fold  # noqa: E402
from common import MODELS_DIR, OUT_DIR, SEED, load_proba, save_json  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DEFER_BITS = 16          # 64 KB per weight table; the device needs two (fix and break vs no change): 128 KB
CONF_BINS = np.linspace(0.5, 1.0, 11)
LEN_BINS = np.array([0, 50, 100, 150, 200, 300, 400, 600, 1000, np.inf])
RATES = np.round(np.arange(0, 1.0001, 0.01), 2)
TARGETS = [0.05, 0.10, 0.20, 0.30]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--chip-prefix", default="chip", help="chip predictions: outputs/{prefix}_{split}_proba.npy")
    p.add_argument("--hub-prefix", default="bert", help="hub predictions, same naming")
    p.add_argument("--defer-cache", default="defer", help="hashed deferral slice in data/cache/hashed_2p20")
    p.add_argument("--tag", default="", help="suffix for output files (empty keeps the original names)")
    return p.parse_args()


def load_cached(name):
    z = np.load(CACHE / f"{name}.npz")
    return binary_csr(z["indices"], indptr=z["indptr"]), z["labels"].astype(int)


def dense_features(p_chip, B):
    """One-hot bins of chip confidence and review length: cheap for the device, non-linear for the model."""
    conf = np.maximum(p_chip, 1 - p_chip)
    n_grams = np.diff(B.indptr)
    c = np.clip(np.digitize(conf, CONF_BINS[1:-1]), 0, len(CONF_BINS) - 2)
    l = np.clip(np.digitize(n_grams, LEN_BINS[1:-1]), 0, len(LEN_BINS) - 2)
    rows = np.arange(len(conf))
    C = sp.csr_matrix((np.ones(len(rows)), (rows, c)), shape=(len(rows), len(CONF_BINS) - 1))
    L = sp.csr_matrix((np.ones(len(rows)), (rows, l)), shape=(len(rows), len(LEN_BINS) - 1))
    return sp.hstack([C, L], format="csr")


def router_features(B, p_chip, with_text=True):
    parts = [dense_features(p_chip, B)]
    if with_text:
        parts.insert(0, normalize(fold(B, DEFER_BITS).astype(np.float64)))
    return sp.hstack(parts, format="csr")


def gain(p_chip, p_hub, y):
    return ((p_hub >= 0.5) == y).astype(int) - ((p_chip >= 0.5) == y).astype(int)


def fit_router(X_tr, g_tr, X_va, g_va, p_chip_va, p_hub_va, y_va):
    """Pick C by accuracy at a 10% send rate on the deferral-validation slice."""
    best = None
    for C in [0.1, 0.3, 1, 3, 10]:
        clf = LogisticRegression(C=C, max_iter=2000, random_state=SEED).fit(X_tr, g_tr)
        score = route_score(clf, X_va)
        acc = accuracy_at_rate(score, p_chip_va, p_hub_va, y_va, 0.10)
        print(f"    C={C}: accuracy at 10% sent {acc:.4f}", flush=True)
        if best is None or acc > best[0]:
            best = (acc, C, clf)
    return best[2], best[1]


def route_score(clf, X):
    proba = clf.predict_proba(X)
    classes = list(clf.classes_)
    return proba[:, classes.index(1)] - proba[:, classes.index(-1)]


def send_mask(score, rate):
    if rate <= 0:
        return np.zeros(len(score), bool)
    k = int(round(rate * len(score)))
    mask = np.zeros(len(score), bool)
    mask[np.argsort(-score, kind="stable")[:k]] = True
    return mask


def accuracy_at_rate(score, p_chip, p_hub, y, rate):
    sent = send_mask(score, rate)
    return float(np.where(sent, (p_hub >= 0.5) == y, (p_chip >= 0.5) == y).mean())


def breakdown(sent, p_chip, p_hub, y):
    g = gain(p_chip, p_hub, y)
    chip_right = (p_chip >= 0.5) == y
    n = max(int(sent.sum()), 1)
    return {"sent_share": float(sent.mean()),
            "accuracy": float(np.where(sent, (p_hub >= 0.5) == y, chip_right).mean()),
            "sent_fixed": float((g[sent] == 1).sum() / n),
            "sent_broken": float((g[sent] == -1).sum() / n),
            "sent_already_right": float((chip_right[sent] & (g[sent] == 0)).sum() / n),
            "sent_both_wrong": float((~chip_right[sent] & (g[sent] == 0)).sum() / n)}


def mcnemar(sent_a, sent_b, p_chip, p_hub, y):
    """Exact paired test of router a vs router b on the same reviews (b/c = discordant counts)."""
    right_a = np.where(sent_a, (p_hub >= 0.5) == y, (p_chip >= 0.5) == y)
    right_b = np.where(sent_b, (p_hub >= 0.5) == y, (p_chip >= 0.5) == y)
    a_only, b_only = int((right_a & ~right_b).sum()), int((~right_a & right_b).sum())
    p = binomtest(a_only, a_only + b_only).pvalue if a_only + b_only else 1.0
    return {"a_only_right": a_only, "b_only_right": b_only, "p_value": float(p)}


def main():
    args = parse_args()
    suffix = f"_{args.tag}" if args.tag else ""
    B_def, y_def = load_cached(args.defer_cache)
    B_val, y_val = load_cached("val")
    B_test, y_test = load_cached("test")
    pc = {s: load_proba(args.chip_prefix, s) for s in ("defer", "val", "test")}
    ph = {s: load_proba(args.hub_prefix, s) for s in ("defer", "val", "test")}
    for s, y in [("defer", y_def), ("val", y_val), ("test", y_test)]:
        assert len(pc[s]) == len(ph[s]) == len(y), f"{s}: {len(pc[s])} chip, {len(ph[s])} hub, {len(y)} labels"

    g_def = gain(pc["defer"], ph["defer"], y_def)
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(y_def))
    tr, va = idx[:250_000], idx[250_000:]
    print(f"deferral slice: {np.mean(g_def == 1):.1%} fixable, {np.mean(g_def == -1):.1%} breakable", flush=True)

    routers, scores = {}, {}
    for name, with_text in [("learned", True), ("learned_no_text", False)]:
        print(f"training {name} router", flush=True)
        X_def = router_features(B_def, pc["defer"], with_text)
        clf, C = fit_router(X_def[tr], g_def[tr], X_def[va], g_def[va], pc["defer"][va], ph["defer"][va], y_def[va])
        routers[name] = {"C": C}
        scores[name] = {s: route_score(clf, router_features(B, pc[s], with_text))
                        for s, B in [("val", B_val), ("test", B_test)]}
        if with_text:
            np.savez(MODELS_DIR / f"defer_router{suffix}.npz", coef=clf.coef_, intercept=clf.intercept_,
                     classes=clf.classes_, bits=DEFER_BITS, conf_bins=CONF_BINS, len_bins=LEN_BINS)
    scores["confidence"] = {s: 1 - np.maximum(pc[s], 1 - pc[s]) for s in ("val", "test")}
    oracle = (gain(pc["test"], ph["test"], y_test) == 1).astype(float)

    curves = {name: [accuracy_at_rate(sc["test"], pc["test"], ph["test"], y_test, r) for r in RATES]
              for name, sc in scores.items()}
    curves["oracle"] = [accuracy_at_rate(oracle + 1e-9 * scores["confidence"]["test"], pc["test"], ph["test"],
                                         y_test, r) for r in RATES]

    hub_acc = float(((ph["test"] >= 0.5) == y_test).mean())
    chip_acc = float(((pc["test"] >= 0.5) == y_test).mean())
    operating, sent = {}, {}
    for name in ("confidence", "learned", "learned_no_text"):
        operating[name], sent[name] = {}, {}
        for t in TARGETS:
            thr = np.quantile(scores[name]["val"], 1 - t)  # threshold chosen on val
            sent[name][f"{int(t * 100)}%"] = scores[name]["test"] > thr
            operating[name][f"{int(t * 100)}%"] = breakdown(sent[name][f"{int(t * 100)}%"], pc["test"], ph["test"], y_test)
        val_acc = [accuracy_at_rate(scores[name]["val"], pc["val"], ph["val"], y_val, r) for r in RATES]
        best_rate = float(RATES[int(np.argmax(val_acc))])  # first (lowest) rate on ties
        thr = np.quantile(scores[name]["val"], 1 - best_rate) if best_rate > 0 else np.inf
        sent[name]["val_best"] = scores[name]["test"] > thr
        operating[name]["val_best"] = {"val_rate": best_rate, "val_accuracy": float(max(val_acc)),
                                       **breakdown(sent[name]["val_best"], pc["test"], ph["test"], y_test)}
    # Learned (a) vs confidence routing (b) at each val-chosen operating point, on test.
    paired = {k: mcnemar(sent["learned"][k], sent["confidence"][k], pc["test"], ph["test"], y_test)
              for k in sent["learned"]}
    match = {name: next((float(r) for r, a in zip(RATES, c) if a >= hub_acc), None) for name, c in curves.items()}

    results = {"chip_prefix": args.chip_prefix, "hub_prefix": args.hub_prefix, "defer_cache": args.defer_cache,
               "chip_test_accuracy": chip_acc, "hub_test_accuracy": hub_acc,
               "deferral_slice": {"fixable": float(np.mean(g_def == 1)), "breakable": float(np.mean(g_def == -1))},
               "routers": routers, "operating_points_test": operating, "learned_vs_confidence_mcnemar": paired,
               "send_rate_to_match_hub": match, "curves_test": {"rates": RATES.tolist(), **curves}}
    save_json(f"defer_results{suffix}.json", results)
    plot(RATES, curves, chip_acc, hub_acc, OUT_DIR / f"defer_curve{suffix}.png")

    print(f"chip alone {chip_acc:.4f}, hub alone {hub_acc:.4f}")
    for name in ("confidence", "learned_no_text", "learned"):
        pts = "  ".join(f"{k}: {v['accuracy']:.4f} ({v['sent_share']:.1%})" for k, v in operating[name].items())
        print(f"{name:16s} {pts}   matches hub at {match[name]}")
    print("learned vs confidence (McNemar p):", "  ".join(f"{k}: {v['p_value']:.2f}" for k, v in paired.items()))


def plot(rates, curves, chip_acc, hub_acc, path):
    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    style = {"learned": ("#2a78d6", "Learned deferral (ours)", "-"),
             "confidence": ("#eb6834", "Confidence routing", "-"),
             "oracle": (ink2, "Perfect router (upper bound)", (0, (1, 2)))}
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200, facecolor=surface)
    ax.set_facecolor(surface)
    x = np.asarray(rates) * 100
    y = {key: np.asarray(curves[key]) * 100 for key in style}
    for key in ("oracle", "confidence", "learned"):
        color, label, ls = style[key]
        ax.plot(x, y[key], color=color, lw=2, ls=ls, label=label, zorder=3 if key == "learned" else 2)
    # Direct labels where the curves are apart: the upper router at 50% sent, the lower one at 25%
    # (clear of the hub line), the oracle at its peak.
    i, k = int(np.argmin(np.abs(x - 50))), int(np.argmin(np.abs(x - 25)))
    upper, lower = sorted(("learned", "confidence"), key=lambda key: -y[key][i])
    ax.text(x[i], y[upper][i] + 0.06, style[upper][1], color=ink, fontsize=9, ha="center", va="bottom")
    ax.text(x[k], y[lower][k] - 0.06, style[lower][1], color=ink, fontsize=9, ha="center", va="top")
    j = int(np.argmax(y["oracle"]))
    ax.text(x[j] + 1.5, y["oracle"][j], style["oracle"][1], color=ink2, fontsize=9, va="center")
    ax.axhline(hub_acc * 100, color=ink2, lw=1, ls=(0, (4, 3)))
    ax.text(59, hub_acc * 100 - 0.06, f"Hub alone  {hub_acc:.2%}", color=ink2, fontsize=9, ha="right", va="top")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_xlim(0, 60)
    lo = chip_acc * 100 - 0.5
    ax.set_ylim(lo, max(max(curves["oracle"]) * 100, hub_acc * 100) + 0.6)
    ax.set_xlabel("Reviews sent to the hub (%)", color=ink2, fontsize=9.5)
    ax.set_ylabel("Test accuracy (%)", color=ink2, fontsize=9.5)
    ax.set_title("Which reviews to send: learned deferral vs. confidence routing (test set)",
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


if __name__ == "__main__":
    main()
