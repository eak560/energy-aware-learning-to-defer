"""Final ensemble and the single test evaluation.

All choices are made on val_pool (50k reviews from movies no model trained on):
  - per transformer: standard head+tail prediction vs. sliding-window ("chunked")
  - which members to combine, and how (mean of logits vs. a logistic-regression
    stacker), scored by 5-fold cross-validation on val_pool
The chosen configuration is fitted on all of val_pool and applied to the test
set once. Every single model's test score is reported too, but none is used to
choose anything.

Test-set statistics: 95% bootstrap confidence interval, exact McNemar tests
against the best single model and the official-data-only baseline, and
accuracy on a de-duplicated test set (test reviews that repeat another test
review or a training review removed).

    python -I src/ensemble.py
"""

import itertools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from scipy.stats import binomtest  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import StratifiedKFold  # noqa: E402

from common import OUT_DIR, ROOT, SEED, clean_text, load_split, save_json  # noqa: E402

MODAL_DIR = ROOT / "outputs_modal"
TRANSFORMERS = ["roberta_large_1m", "electra_large_1m", "deberta_v3_large_1m"]
NGRAM = ["ngram1024KB"]
BASELINE = "roberta_large_official"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def load(prefix, split):
    for d in (MODAL_DIR, OUT_DIR):
        f = d / f"{prefix}_{split}_proba.npy"
        if f.exists():
            return np.load(f).astype(np.float64)
    return None


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def acc(y, p):
    return float(((p >= 0.5) == y).mean())


def cv_accuracy(X, y, method):
    """5-fold CV accuracy on val_pool for a combination method over logit features X."""
    if method == "mean":
        return acc(y, 1 / (1 + np.exp(-X.mean(axis=1))))
    correct = 0
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=SEED).split(X, y):
        clf = LogisticRegression(C=1.0).fit(X[tr], y[tr])
        correct += int((clf.predict(X[te]) == y[te]).sum())
    return correct / len(y)


def bootstrap_ci(correct, n_boot=2000):
    rng = np.random.default_rng(SEED)
    stats = [correct[rng.integers(0, len(correct), len(correct))].mean() for _ in range(n_boot)]
    return [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))]


def mcnemar(correct_a, correct_b):
    b = int((correct_a & ~correct_b).sum())
    c = int((~correct_a & correct_b).sum())
    return {"a_only_right": b, "b_only_right": c,
            "p_value": float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0}


def dedup_mask():
    """True for test reviews that are not a duplicate of another test review or of a train/val review."""
    norm = lambda t: _NON_ALNUM.sub("", clean_text(t).lower())
    train_keys = {norm(t) for s in ("train", "val") for t in load_split(s)["text"]}
    test_keys = [norm(t) for t in load_split("test")["text"]]
    counts = {}
    for k in test_keys:
        counts[k] = counts.get(k, 0) + 1
    return np.array([counts[k] == 1 and k not in train_keys for k in test_keys])


def main():
    y_vp = pq.read_table(ROOT / "data" / "pool" / "splits_v2" / "val_pool.parquet", columns=["label"]).column("label").to_numpy()
    y_test = load_split("test")["label"].to_numpy()

    # 1. Each member: pick standard vs chunked on val_pool.
    members, singles = {}, {}
    for prefix in TRANSFORMERS + NGRAM + [BASELINE]:
        options = {}
        for variant in (prefix, f"{prefix}_chunked"):
            vp, te = load(variant, "val_pool"), load(variant, "test")
            if vp is not None and te is not None:
                options[variant] = (vp, te)
        if not options:
            print(f"skipping {prefix}: no predictions found", flush=True)
            continue
        chosen = max(options, key=lambda v: acc(y_vp, options[v][0]))
        vp, te = options[chosen]
        singles[prefix] = {"variant": chosen, "val_pool": acc(y_vp, vp), "test": acc(y_test, te),
                           "val_pool_by_variant": {v: acc(y_vp, o[0]) for v, o in options.items()}}
        if prefix != BASELINE:
            members[prefix] = (vp, te)
    print(json.dumps(singles, indent=1), flush=True)

    # 2. Pick the subset and combination method by 5-fold CV on val_pool.
    names = list(members)
    candidates = []
    for k in range(1, len(names) + 1):
        for subset in itertools.combinations(names, k):
            X = np.column_stack([logit(members[n][0]) for n in subset])
            for method in (("mean", "stack") if k > 1 else ("mean",)):
                candidates.append({"members": list(subset), "method": method, "val_pool_cv": cv_accuracy(X, y_vp, method)})
    candidates.sort(key=lambda c: -c["val_pool_cv"])
    best = candidates[0]
    print("top configurations on val_pool:", json.dumps(candidates[:5], indent=1), flush=True)
    if "--val-only" in sys.argv:  # look at combinations without touching the test set
        return

    # 3. Fit the chosen configuration on all of val_pool, evaluate on test once.
    X_vp = np.column_stack([logit(members[n][0]) for n in best["members"]])
    X_te = np.column_stack([logit(members[n][1]) for n in best["members"]])
    if best["method"] == "stack":
        stacker = LogisticRegression(C=1.0).fit(X_vp, y_vp)
        p_test = stacker.predict_proba(X_te)[:, 1]
        best["stacker_weights"] = dict(zip(best["members"], stacker.coef_[0].round(4).tolist()))
    else:
        p_test = 1 / (1 + np.exp(-X_te.mean(axis=1)))
    correct = (p_test >= 0.5) == y_test

    best_single = max((n for n in singles if n != BASELINE), key=lambda n: singles[n]["val_pool"])
    single_correct = (members[best_single][1] >= 0.5) == y_test
    keep = dedup_mask()
    result = {
        "chosen_on_val_pool": best,
        "test_accuracy": float(correct.mean()),
        "test_accuracy_95ci": bootstrap_ci(correct),
        "test_accuracy_deduplicated": float(correct[keep].mean()),
        "deduplicated_test_reviews": int(keep.sum()),
        "best_single_by_val_pool": best_single,
        "mcnemar_vs_best_single": mcnemar(correct, single_correct),
        "singles": singles,
        "reference_records": {"ERNIE-Doc-Large (ACL 2021)": 0.971, "XLNet (NeurIPS 2019)": 0.968,
                              "LlamBERT (2024, extra data)": 0.9668, "RoBERTa-large (official data)": 0.9654},
    }
    if BASELINE in singles:
        base = load(singles[BASELINE]["variant"], "test")
        result["mcnemar_vs_official_baseline"] = mcnemar(correct, (base >= 0.5) == y_test)
    save_json("ensemble_results.json", result)
    print(json.dumps({k: result[k] for k in ("chosen_on_val_pool", "test_accuracy", "test_accuracy_95ci",
                                             "test_accuracy_deduplicated", "mcnemar_vs_best_single")}, indent=1))


if __name__ == "__main__":
    main()
