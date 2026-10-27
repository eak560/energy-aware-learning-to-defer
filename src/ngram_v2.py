"""Retrain the hashed n-gram models on the cleaned v2 pool, for the ensemble.

The Phase 2 models were trained on the v1 pool, which still contained reviews
by test-review authors and some reviews of test-set movies. This retrains the
1 MB and 256 KB models on official train + splits_v2/chip_train (movie- and
author-disjoint from test), picks alpha on val_pool, and writes
outputs/ngram{1024,256}KB_{val,val_pool,test,defer}_proba.npy (defer = the
splits_v2 deferral slice, held out from chip and hub training) plus the int8
device weights to outputs/models/ngram{1024,256}KB_v2.npz.

    python -I src/ngram_v2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402

from chip_model import cached, device_proba, fit_and_score, from_parquet, from_split  # noqa: E402
from common import MODELS_DIR, ROOT, metrics, save_json, save_proba  # noqa: E402

V2 = ROOT / "data" / "pool" / "splits_v2"


def main():
    B_maas, y_maas = cached("maas_train", from_split("train"))
    B_val, y_val = cached("val", from_split("val"))
    B_test, y_test = cached("test", from_split("test"))
    B_vp, y_vp = cached("val_pool_v2", from_parquet(V2 / "val_pool.parquet"))
    B_def, y_def = cached("defer_v2", from_parquet(V2 / "defer.parquet"))
    B_pool, y_pool = cached("chip_train_v2", from_parquet(V2 / "chip_train.parquet"))
    B = sp.vstack([B_maas, B_pool], format="csr")
    y = np.concatenate([y_maas, y_pool])
    del B_pool
    report = {"train_reviews": int(len(y))}
    for bits in (20, 18):
        best = fit_and_score(B, y, len(y), B_vp, y_vp, bits, [1e-8, 3e-8, 1e-7])
        name = f"ngram{2 ** bits // 1024}KB"
        report[name] = {"alpha": best["alpha"], "alpha_at_grid_edge": best["alpha_at_grid_edge"]}
        q, scale, bias = best["weights"]
        np.savez(MODELS_DIR / f"{name}_v2.npz", weights=q, scale=scale, bias=bias, bits=bits, ngram_max=2)
        for split, Bs, ys in [("val", B_val, y_val), ("val_pool", B_vp, y_vp), ("test", B_test, y_test),
                              ("defer", B_def, y_def)]:
            p = device_proba(Bs, bits, best["weights"])
            save_proba(name, split, p)
            report[name][split] = metrics(ys, p >= 0.5)
        print(name, report[name], flush=True)
    save_json("ngram_v2_results.json", report)


if __name__ == "__main__":
    main()
