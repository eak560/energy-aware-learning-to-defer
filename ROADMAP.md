# Roadmap: energy-aware learning to defer

The project's contribution combines both twists into one method:

> A battery-powered device runs a tiny sentiment model on-device. A second
> tiny model (the **deferral model**) predicts whether a transformer on a
> nearby hub would fix the device's answer (**learning to defer**). The device
> only sends text to the hub when that predicted gain is worth the energy the
> radio and remote compute cost (**energy-aware routing**).

## Who needs it: battery-powered devices that handle text or speech

The method is device-agnostic. **Robots are one of the biggest use cases**, not
the only one:

- **Robots (social, assistive, eldercare):** computing is a major battery drain
  (motors are only 16.6-54.6% of measured robot power, Liu et al. 2025), and
  big onboard models cost hours of battery (Pohland et al. 2026).
- **Off-grid mesh messengers:** text typed straight into a battery-powered
  ESP32-S3 (e.g. LILYGO T-Deck running Meshtastic).
- **Wearables:** a smartwatch with the phone as the hub.
- **Smart toys, battery or solar feedback terminals.**

Our prototype targets the smallest tier: an ESP32 device with a Raspberry Pi
Zero 2 W hub. Slide-ready wording for these use cases is in
[`slides/upcoming_slides_content.md`](slides/upcoming_slides_content.md).

## The decision rule

For each review `x`, the chip computes:

- `p(x)`: its own P(positive), from the 256 KB-1 MB hashed n-gram model
- `g(x)`: the deferral model's estimate of the accuracy gained by sending `x` to the hub

It sends `x` to the hub only if:

```
g(x) > λ        λ = how much one Wi-Fi send "costs", in accuracy units
```

- **Confidence routing** (what we have now) is the special case `g(x) ≈ 1 − confidence(x)`. It only knows "I might be wrong", not "the hub would get this right".
- **Learning to defer** learns `g(x)` from data, so it stops sending reviews the hub would also get wrong, or that the chip already gets right.
- **Energy-aware** means λ comes from the battery budget. Sweeping λ traces **accuracy vs. battery life**, measured on real hardware.

## Phases

| # | Phase | Output | Needs |
|---|---|---|---|
| 0 | ✅ Baseline cascade | Fast model 90.28%, DistilBERT 93.51%, cascade matches DistilBERT at 28% sent | done |
| 1 | ✅ **Leakage-free data pool** | 4.1M IMDb + 12.0M Amazon clean reviews; 23,818 copies of test reviews removed; reviews of test-set movies flagged | done |
| 2 | ✅ Stronger chip model | 256 KB int8 model trained on 1.94M reviews: **92.69% test** (was 90.28%); 1 MB: 93.12% val. Test-movie leak ablation +0.02 pts (negligible); Amazon adds nothing (−0.13 test) | done |
| 3 | ✅ Hub model | Retrained on official train + 1M leak-free pool reviews (Modal H100): **DistilBERT 95.83% test** (was 93.51%), **RoBERTa-base 96.72%**. Both should fit the Pi Zero 2 W's 512 MB as int8 (~67 MB / ~125 MB); RoBERTa-base needs ~2× DistilBERT's compute per review. Pi latency not yet measured | done; Pi timing in Phase 7 |
| 4 | ✅ Deferral labels | DistilBERT on the 300k held-out slice: hub fixes 4.1%, breaks 3.9% of chip answers. Regenerated on the leak-free v2 slice for the 1M-review hubs: DistilBERT fixes 5.0% / breaks 1.5%, RoBERTa-base 5.4% / 1.2% | done |
| 5 | ✅ **Twist 1: learning to defer** | Cascade beats both models: **94.05% at 10.7% sent**, threshold chosen on val (hub alone 93.51%); matches the hub at ~5% sent. (An earlier "94.07% at 16%" was the maximum of the test curve, i.e. chosen on test, so it is not reported.) Learned deferral ≈ confidence routing (±0.1 pts). **Follow-up done (retrained hub, below): still not a win.** With the 1M-review hubs the hub breaks far fewer chip answers (1.2-1.5% vs 3.9%), but learned deferral stays within ±0.1 pts of confidence routing at every val-chosen send rate, and no gap survives a multiple-comparison correction | done; open: better router features, or lead with Twist 2 |
| 6 | ✅ **Twist 2: energy-aware routing** | Matching the hub's accuracy costs **14-19× less device energy** than sending every review (15.8 vs 300.6 mJ at a 1 s hub wait; ratio holds for 0.1-2 s). Datasheet currents; timings are placeholders until measured. This holds for the old 93.51% hub only: with the 1M-review hubs, fully matching the hub takes 43% sent (DistilBERT) / 92% (RoBERTa-base), while 13-14% sent closes 75% of the chip-hub gap at 40-43 mJ (~7× less than sending all) | done with placeholders; INA219 for real numbers |
| 7 | Hardware | ESP32 firmware (tokenise → hash → int8 lookup → route), Pi Zero hub (int8 ONNX + small HTTP server), measured latency and energy | ESP32-S3, Pi Zero 2 W, INA219 |
| R | ✅ **Record attempt** | Ensemble of ELECTRA-large + DeBERTa-v3-large (each trained with 1M extra leak-free reviews) + 1 MB n-gram: **97.40% test** (95% CI 97.21–97.58) vs ERNIE-Doc 97.1%; extra-data setting. See README "Results" | done (~$18 of Modal credits) |
| 8 | Write-up | Report + slides; all citations in `papers/references.bib` | — |

## Phase 5 follow-up: retrained hub (2026-10-26)

Does a stronger hub make learned deferral beat confidence routing? No.

Setup, all leak-free: hubs trained on official train + the first 1M rows of
`splits_v2/chip_train` (best checkpoint chosen on `val_pool`). Deferral labels come from the
**v2** 300k deferral slice: 94k of the old v1 slice's reviews (31%) are in the new hubs' training
data, while the v2 slice has none. The chip is the v2 256 KB n-gram (92.32% test, never trained on
the slice). Every threshold is chosen on the official val split and applied once to test; the
router's C is chosen on a 50k part of the deferral slice.

Test accuracy (%), **confidence routing / learned deferral** (learned − confidence, exact
McNemar p on the 25k test reviews):

| Hub (test acc.) | Fix / break on deferral slice | 5% sent | 10% | 20% | 30% | Best rate on val |
|---|---|---|---|---|---|---|
| DistilBERT, 20k train (old hub, v1 chip + slice) (93.51%) | 4.1% / 3.9% | 93.63 / 93.64 (+0.01, p=0.94) | 94.05 / 93.92 (−0.12, p=0.04) | 93.91 / 93.98 (+0.07, p=0.28) | 93.81 / 93.95 (+0.14, p=0.10) | 94.07 / 93.99 (−0.08, p=0.22), sent 12% / 17% |
| DistilBERT, +1M pool (95.83%) | 5.0% / 1.5% | 93.71 / 93.68 (−0.03, p=0.64) | 94.70 / 94.75 (+0.05, p=0.24) | 95.48 / 95.54 (+0.06, p=0.07) | 95.72 / 95.72 (+0.00, p=1.00) | 95.83 / 95.82 (−0.02, p=0.57), sent 77% / 78% |
| RoBERTa-base, +1M pool (96.72%) | 5.4% / 1.2% | 93.97 / 93.91 (−0.06, p=0.37) | 95.14 / 95.23 (+0.10, p=0.03) | 96.12 / 96.16 (+0.04, p=0.28) | 96.52 / 96.52 (−0.00, p=1.00) | 96.68 / 96.72 (+0.03, p=0.13), sent 53% / 98% |

- The one nominal win (RoBERTa-base, 10%: +0.10, p = 0.03) is 1 of 15 tests: it fails a
  Bonferroni correction (p < 0.0033), and part of it comes from sending 10.7% vs 10.5% of reviews.
  At exactly 10% sent the gap is +0.04.
- What changed: the stronger hub almost never breaks a chip answer (1.2% vs 3.9%), so most of what
  learned deferral could avoid sending has disappeared. The remaining job is finding the
  ~5% the hub fixes, and the n-gram router finds them no better than chip confidence does.
- Router size on the device: 2^16 hash buckets, but the 3-class score needs two int8 weight tables
  (fix and break logits relative to no change), so 128 KB, not 64 KB. With the 256 KB chip model the
  device uses 384 KB of the ESP32-S3's 512 KB SRAM. The paper, slides and scripts say 128 KB.
  A perfect router would reach 97.3-97.5% at 5-10% sent, so the headroom is real.
- Confidence cascade (`cascade.py`, τ chosen on val within 0.5 pts of the hub): 95.45% at 20.0%
  sent (DistilBERT-1M), 96.11% at 20.5% sent (RoBERTa-base-1M).
- Modal cost: $2.56, itemised per run by `modal billing report` (RoBERTa-base $1.64, DistilBERT
  $0.91, DistilBERT tokenize $0.02). RoBERTa-base reused the RoBERTa-large token cache, since the
  tokenizers are identical.

Reproduce (outputs are `*_distilbert_1m.*`, `*_roberta_base_1m.*`; the old hub is `*_v1_distilbert20k.*`):

```bash
python -m modal run --detach src/modal_app.py::train --gpu H100 --max-hours 1 --args "--model roberta-base --pool-reviews 1000000 --prefix roberta_base_1m --lr 2e-5 --batch-size 32 --accum 1"
python -m modal run --detach src/modal_app.py::train --gpu H100 --max-hours 0.75 --args "--model distilbert-base-uncased --pool-reviews 1000000 --prefix distilbert_1m --lr 3e-5 --batch-size 32 --accum 1"
python -I src/ngram_v2.py   # v2 chip, now also scores the v2 deferral slice
python -I src/defer_router.py --chip-prefix ngram256KB --defer-cache defer_v2 --hub-prefix roberta_base_1m --tag roberta_base_1m
python -I src/energy_curves.py --tag roberta_base_1m
python src/cascade.py --fast-prefix ngram256KB --bert-prefix roberta_base_1m --benchmark 0 --tag roberta_base_1m
```

## Data rules (Phase 1)

- **Labels:** IMDb rating ≤ 4/10 → negative, ≥ 7/10 → positive (Maas et al. 2011 rule); Amazon 1-2 stars → negative, 4-5 → positive. Middle ratings and missing ratings are dropped.
- **Test set never changes:** the official IMDb 25k test split, so results stay comparable with published work.
- **Leakage removal:** the Kaggle scrape and the official test set both come from IMDb. Any pool review whose normalised text matches a val or test review is dropped. The count dropped is reported, because a near-99% result is the giveaway that this step was skipped.
- **Pool splits:** chip-training / deferral-label / pool-validation slices, so the hub never labels reviews it trained on.

## Suggested team split

| Person | Owns |
|---|---|
| ML | Phases 2-6 (models, deferral, curves) |
| Hardware | Phase 7 (ESP32 firmware, Pi hub, INA219 measurements) |
| Write-up | Phase 8, related-work section from `papers/`, figures |
