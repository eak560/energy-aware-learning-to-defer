"""How small can the on-device model get and stay accurate?

Hashed n-gram logistic regression sized for an ESP32. Hashing removes the
vocabulary entirely: the device only stores one int8 weight per hash bucket
(2^18 buckets = 256 KB) and computes

    score = bias + sum(weight[hash(ngram)] for each distinct n-gram) / sqrt(#n-grams)

Optional NB scaling (Wang & Manning 2012) is folded into the same weight table,
so it costs nothing on the device. Evaluated on the val split only; test stays
untouched. C is picked on val too, so these numbers are slightly optimistic and
are for sizing decisions, not for the final report.
"""

import time

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import normalize

from common import load_split, save_json


def nb_ratio(X, y, alpha=1.0):
    """Log-count ratio r per feature: how much more often it appears in positive reviews."""
    p = alpha + np.asarray(X[y == 1].sum(axis=0)).ravel()
    q = alpha + np.asarray(X[y == 0].sum(axis=0)).ravel()
    return np.log((p / p.sum()) / (q / q.sum()))


def quantize_int8(w):
    scale = np.abs(w).max() / 127
    return np.clip(np.round(w / scale), -127, 127) * scale


def main():
    train, val = load_split("train"), load_split("val")
    y_tr, y_va = train["label"].to_numpy(), val["label"].to_numpy()
    results = []
    for ngram in [(1, 2), (1, 3)]:
        for bits in [14, 16, 18, 20]:
            hv = HashingVectorizer(n_features=2 ** bits, ngram_range=ngram, alternate_sign=False,
                                   binary=True, norm=None)
            t0 = time.perf_counter()
            B_tr, B_va = hv.transform(train["text"]), hv.transform(val["text"])
            X_tr, X_va = normalize(B_tr), normalize(B_va)  # binary, L2-normalised
            vec_s = time.perf_counter() - t0
            for use_nb in (False, True):
                r = nb_ratio(B_tr, y_tr) if use_nb else np.ones(2 ** bits)
                Xs_tr, Xs_va = X_tr.multiply(r).tocsr(), X_va.multiply(r).tocsr()
                best = None
                for C in (1, 4, 16, 64):
                    clf = LogisticRegression(C=C, max_iter=3000).fit(Xs_tr, y_tr)
                    acc = (clf.predict(Xs_va) == y_va).mean()
                    if best is None or acc > best[0]:
                        best = (acc, C, clf)
                acc, C, clf = best
                # Fold r into the weights: the device stores a single int8 table.
                w_folded = clf.coef_[0] * r
                w_q = quantize_int8(w_folded)
                acc_q = (((X_va @ w_q + clf.intercept_[0]) > 0).astype(int) == y_va).mean()
                row = {"ngram": f"1-{ngram[1]}", "buckets": f"2^{bits}", "nb": use_nb, "C": C,
                       "val_acc_float": round(float(acc), 4), "val_acc_int8": round(float(acc_q), 4),
                       "model_kb_int8": 2 ** bits / 1024, "vectorise_s": round(vec_s, 1)}
                results.append(row)
                print(row, flush=True)
    save_json("esp32_feasibility.json", {"rows": results})


if __name__ == "__main__":
    main()
