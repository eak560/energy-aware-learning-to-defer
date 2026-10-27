# Cascade Sentiment Analysis

A hybrid sentiment classifier for IMDb movie reviews. A fast TF-IDF + logistic
regression model reads every review. Only the reviews it is unsure about are
sent to a fine-tuned DistilBERT transformer.

**Research question:** how much of a transformer's accuracy can we keep while
running it on only a fraction of the reviews?

```
review ──► TF-IDF + LR ──► confident? ──yes──► answer
                               │
                               no (confidence < τ)
                               ▼
                          DistilBERT ──► answer
```

Why the two models complement each other:

- **TF-IDF + LR** reads the whole review and is very fast, but it ignores word
  order, so it misses sarcasm and some longer negations.
- **DistilBERT** understands context, but it can only read 512 tokens. We keep
  the first 128 and last 382 tokens of long reviews (head + tail truncation,
  Sun et al. 2019).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run the pipeline

Run from the project folder, in order:

| Step | Command | What it does | Time (M3 Pro) |
|---|---|---|---|
| 1 | `.venv/bin/python src/prepare_data.py` | Downloads IMDb and writes `data/splits/`: train 20k, val 5k, test 25k | ~1 min |
| 2 | `.venv/bin/python src/fast_model.py` | TF-IDF + LR with `C` tuned by 3-fold CV on train | ~1 min |
| 3 | `.venv/bin/python src/train_transformer.py` | Fine-tunes DistilBERT for 2 epochs (cuda > mps > cpu) | ~1 hour |
| 4 | `.venv/bin/python src/cascade.py` | Picks τ on val, evaluates on test, benchmarks speed | ~2 min |

### Large review pool (Phase 1 of [ROADMAP.md](ROADMAP.md))

The raw downloads go in `data/raw/` (git-ignored). They are untrusted files,
so these scripts run with `python -I` and take the paths as arguments.

| Step | Command | What it does |
|---|---|---|
| 5 | `.venv/bin/kaggle datasets download ebiswas/imdb-review-dataset -p data/raw/kaggle_imdb --unzip` | 5.5M IMDb reviews (7.8 GB). Needs a Kaggle token in `~/.kaggle/access_token` |
| 6 | `curl -L -C - -o data/raw/amazon_movies_tv/Movies_and_TV.jsonl https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/review_categories/Movies_and_TV.jsonl` | 17.3M Amazon Movies & TV reviews (8.4 GB) |
| 7 | `.venv/bin/python -I src/build_pool.py --imdb data/raw/kaggle_imdb/part-0*.json --report pool_report_imdb.json` | Labels, de-duplicates and removes every review matching our train/val/test splits → `data/pool/imdb.parquet` |
| 8 | `.venv/bin/python -I src/build_pool.py --amazon data/raw/amazon_movies_tv/Movies_and_TV.jsonl --report pool_report_amazon.json` | Same for Amazon → `data/pool/amazon.parquet` |
| 9 | `.venv/bin/python -I src/maas_movies.py --acl data/raw/acl_imdb/aclImdb --titles data/raw/imdb_titles/title.basics.tsv.gz` | Lists the official train/test movies so pool reviews *of test movies* can be excluded or measured |

Step 9 needs the original [aclImdb archive](https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz) (for `urls_*.txt`) and IMDb's [title.basics.tsv.gz](https://datasets.imdbws.com/). It also writes `data/pool/imdb_test_movie_flag.npy`, which step 10 needs.

### Energy-aware learning to defer (Phases 2-6 of [ROADMAP.md](ROADMAP.md))

| Step | Command | What it does | Time (M3 Pro) |
|---|---|---|---|
| 10 | `.venv/bin/python -I src/pool_splits.py` | Balanced slices: 1.92M chip-training, 300k deferral (held out), test-movie and Amazon ablation sets | ~1 min |
| 11 | `.venv/bin/python -I src/chip_model.py` | On-device model (hashed n-grams, int8, 256 KB / 1 MB): accuracy vs. data size, NB on/off, leak and Amazon ablations | ~45 min |
| 12 | `.venv/bin/python -I src/hub_labels.py` | DistilBERT predictions on the 300k deferral slice | ~35 min |
| 13 | `.venv/bin/python -I src/defer_router.py` | Trains the deferral model; compares learned deferral, confidence routing and a perfect router on test | ~5 min |
| 14 | `.venv/bin/python -I src/energy_curves.py` | Device energy per review for each router (datasheet currents; timings are placeholders until measured) | seconds |

Steps 11 and 12 can run at the same time (CPU and GPU).

### Record attempt: large models on Modal cloud GPUs

Large encoders (RoBERTa-large, DeBERTa-v3-large) are too slow on an Apple GPU
(~3.6 reviews/s), so they train on Modal ([`src/modal_app.py`](src/modal_app.py)).
Leak cleaning round 2 runs first:

| Step | Command | What it does |
|---|---|---|
| 15 | `.venv/bin/python -I src/pool_hygiene.py` | Flags test-movie, test-author and near-duplicate reviews; builds `data/pool/splits_v2/` (movie- and author-disjoint from test) incl. a 50k movie-disjoint `val_pool` |
| 16 | `.venv/bin/python -m modal setup` | **Run this yourself**: signs in to Modal through your browser |
| 17 | `.venv/bin/python -m modal run src/modal_app.py::upload` | Uploads ~1.2 GB of splits to a Modal volume (once) |
| 18 | `.venv/bin/python -m modal run src/modal_app.py::tokenize --model roberta-large --pool-reviews 1000000` | Caches tokens on a CPU machine (no GPU billing) |
| 19 | `.venv/bin/python -m modal run --detach src/modal_app.py::train --gpu H100 --args "--model roberta-large --pool-reviews 1000000 --prefix roberta_large_1m --lr 1e-5 --batch-size 32 --accum 1"` | Trains on an H100; best checkpoint chosen on `val_pool`; resumable |
| 20 | `.venv/bin/python -m modal volume get ai-sentiment outputs ./outputs_modal` | Downloads predictions and metrics |

To smoke-test step 3, run `--limit 200 --epochs 1 --prefix smoke`. If training is
too slow on your machine, use
[`notebooks/train_distilbert_colab.ipynb`](notebooks/train_distilbert_colab.ipynb)
on a free Colab GPU, then unzip its output into `outputs/`.

## Outputs

| File | Contents |
|---|---|
| `outputs/results_table.md` | Final test-set comparison: accuracy, F1, % routed, reviews/sec |
| `outputs/cascade_curve.png` | Validation accuracy vs. % of reviews sent to DistilBERT |
| `outputs/cascade_results.json` | Everything: chosen τ, sweep, stacker weights, benchmark, accuracy by review length |
| `outputs/error_analysis.csv` | 30 test reviews each where DistilBERT fixed / broke / shared the fast model's mistake. Fill in the `tag` column by hand |
| `outputs/{fast,bert}_metrics.json` | Per-model details: best C, top words, training history, truncation share |

## Methodology notes

- **The test set is used once.** `C` is tuned by cross-validation on train. The
  threshold τ and the stacked ensemble are fitted on val. Test is only used to
  report final numbers.
- **τ selection rule, fixed in advance:** the fewest reviews routed while
  staying within 0.5 accuracy points of DistilBERT alone on val
  (`--tolerance`).
- **The stacked ensemble** is an upper-bound reference. It runs both models on
  every review and learns how to weight them, which shows what the cascade
  gives up in exchange for speed.
- **Speed is measured end to end** on the same raw test reviews for every
  system, including vectorising and tokenising, after a warm-up pass.

## References

- Maas et al. (2011). *Learning Word Vectors for Sentiment Analysis.* ACL. (IMDb dataset)
- Wang & Manning (2012). *Baselines and Bigrams: Simple, Good Sentiment and Topic Classification.* ACL.
- Sanh et al. (2019). *DistilBERT, a distilled version of BERT.* arXiv:1910.01108.
- Sun et al. (2019). *How to Fine-Tune BERT for Text Classification?* CCL.
- Varshney & Baral (2022). *Model Cascading: Towards Jointly Improving Efficiency and Accuracy of NLP Systems.* EMNLP.

## Project layout

```
src/
  common.py             paths, split loading, metrics
  prepare_data.py       step 1
  fast_model.py         step 2
  train_transformer.py  step 3
  cascade.py            step 4
  esp32_feasibility.py  how small the on-device model can get (hashed n-grams, int8)
  build_pool.py         large leakage-free review pool from Kaggle IMDb + Amazon
  maas_movies.py        which movies are in the official train/test sets
notebooks/
  train_distilbert_colab.ipynb
papers/                 every cited paper, grouped by purpose (see papers/README.md)
  references.bib        BibTeX for all of them
build_deck.js           Review 2 slide deck generator (pptxgenjs)
```

## Results: IMDb record attempt (official 25k test set)

All choices (model variants, ensemble members, stacker) were made on `val_pool`,
50k reviews from movies no model trained on. The test set was scored once for
the final ensemble ([`src/ensemble.py`](src/ensemble.py), results in
`outputs/ensemble_results.json`).

| System | Extra training data | Practice set (val_pool) | Test |
|---|---|---|---|
| RoBERTa-large, official train only (our reproduction) | none | 96.38% | 96.54% |
| RoBERTa-large | 1M leak-free IMDb reviews | 97.24% | 97.21% |
| ELECTRA-large (long reviews read in windows) | 1M | 97.37% | 97.22% |
| DeBERTa-v3-large | 1M | 97.51% | 97.33% |
| **Ensemble: ELECTRA + DeBERTa + 1 MB n-gram (stacked)** | 1M | 97.54% (5-fold CV) | **97.40%** (95% CI 97.21–97.58) |
| *ERNIE-Doc-Large (ACL 2021), previous best peer-reviewed* | none | — | *97.1%* |

- De-duplicated test (24,479 reviews; repeats inside test or of train reviews removed): **97.40%**.
- Ensemble vs. best single model: exact McNemar p = 0.046. Vs. official-data baseline: p ≈ 6 × 10⁻²².
- **How to state it:** "97.40% on the IMDb test set using ~1M additional rating-labelled IMDb reviews, de-duplicated against test and movie- and author-disjoint from it." This belongs in the *extra training data* category, not the official-train-only one.
- Compute: Modal H100s, about $18 in total.
