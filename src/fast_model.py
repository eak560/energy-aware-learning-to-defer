"""Stage 1 of the cascade: TF-IDF (unigrams + bigrams) + logistic regression.

Tunes the regularisation strength C with 3-fold cross-validation on the train
split only, so the val split stays untouched for the router and the stacker.
Saves P(positive) for val and test to outputs/fast_{split}_proba.npy.
"""

import time

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

from common import MODELS_DIR, SEED, load_split, metrics, save_json, save_proba


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),   # bigrams capture short negations like "not good"
            min_df=2,             # drop n-grams seen in only one review
            max_df=0.9,
            sublinear_tf=True,    # 1 + log(tf): a word said 10 times isn't 10x the evidence
        )),
        ("lr", LogisticRegression(max_iter=2000, random_state=SEED)),
    ])


def top_features(pipe: Pipeline, k: int = 15) -> dict:
    names = pipe.named_steps["tfidf"].get_feature_names_out()
    coef = pipe.named_steps["lr"].coef_[0]
    order = np.argsort(coef)
    return {
        "most_negative": [names[i] for i in order[:k]],
        "most_positive": [names[i] for i in order[::-1][:k]],
    }


def main():
    train, val, test = load_split("train"), load_split("val"), load_split("test")

    search = GridSearchCV(
        build_pipeline(),
        param_grid={"lr__C": [2, 4, 8, 16, 32, 64, 128]},
        cv=3, scoring="accuracy", n_jobs=4, verbose=1,
    )
    t0 = time.perf_counter()
    search.fit(train["text"], train["label"])
    train_seconds = time.perf_counter() - t0
    pipe = search.best_estimator_
    print(f"best C = {search.best_params_['lr__C']}  (cv accuracy {search.best_score_:.4f})")

    p_val = pipe.predict_proba(val["text"])[:, 1]
    t0 = time.perf_counter()
    p_test = pipe.predict_proba(test["text"])[:, 1]   # includes vectorising the raw text
    test_seconds = time.perf_counter() - t0

    save_proba("fast", "val", p_val)
    save_proba("fast", "test", p_test)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODELS_DIR / "fast_model.joblib")

    report = {
        "best_C": search.best_params_["lr__C"],
        "cv_accuracy": float(search.best_score_),
        "n_features": len(pipe.named_steps["tfidf"].vocabulary_),
        "val": metrics(val["label"], p_val >= 0.5),
        "test": metrics(test["label"], p_test >= 0.5),
        "test_reviews_per_sec": len(test) / test_seconds,
        "grid_search_seconds": train_seconds,
        **top_features(pipe),
    }
    save_json("fast_metrics.json", report)
    print(f"val  accuracy {report['val']['accuracy']:.4f}  f1 {report['val']['f1']:.4f}")
    print(f"test accuracy {report['test']['accuracy']:.4f}  f1 {report['test']['f1']:.4f}")
    print(f"throughput    {report['test_reviews_per_sec']:,.0f} reviews/sec (CPU)")


if __name__ == "__main__":
    main()
