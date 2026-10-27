# Papers and references

Every paper, dataset and datasheet referred to in this project, grouped by the
job it does. All BibTeX entries are in [`references.bib`](references.bib). The
arXiv and ACL entries come straight from arXiv and the ACL Anthology.

Two papers are paywalled, so their folders hold a `.LINK.md` file with the DOI
or link instead of a PDF. Get those through the VIT library.

The PDFs themselves are not in the public repository, because they belong to
their authors and publishers. Each one can be found from its entry in
`references.bib`.

## 01_datasets — where the training and test data come from

| Paper | Why it's here |
|---|---|
| Maas et al. (2011), *Learning Word Vectors for Sentiment Analysis* | Introduces the IMDb dataset we train and test on (50k labelled + 50k unlabelled reviews). Its rating rule (≤4 negative, ≥7 positive) is how we label larger review collections. |
| Zhang, Zhao & LeCun (2015), *Character-level ConvNets for Text Classification* | Source of the Amazon Polarity (3.6M) and Yelp Polarity (560k) datasets. |
| Hou et al. (2024), *Bridging Language and Items for Retrieval and Recommendation* | Introduces Amazon Reviews 2023 (571M reviews; 17.3M in Movies & TV). |

Also used, with no paper: the Biswas *IMDb Review Dataset* on Kaggle (5.5M reviews, CC0), cited as `biswas_imdb_review_dataset` in `references.bib`.

## 02_accuracy_ceiling_and_benchmarks — how high accuracy can realistically go

| Paper | Why it's here |
|---|---|
| Northcutt et al. (2021), *Pervasive Label Errors in Test Sets* | 725 of IMDb's 25,000 test labels (2.9%) are wrong, so ~97% is the practical ceiling. Any claim near 99% points to leakage. |
| Ding et al. (2021), *ERNIE-Doc* | **97.1% on IMDb: the best peer-reviewed result (ACL 2021)** and the record to beat. A long-document transformer. |
| Csanády et al. (2024), *LlamBERT* | 96.68% (RoBERTa-large + Llama-2 labels on extra IMDb text) and the source of the 96.54% RoBERTa-large baseline. Tagged as an extra-training-data result. |
| Patten et al. (2025), *Combinatorial Fusion* (**preprint**) | Claims 97.07%, but fusion weights and the best of ~90 combinations are picked on the test set. **Not a credible bar**; kept as an example of test-set selection to avoid. |
| Zhang & Arefyev (2022), *Document Vectors Using Cosine Similarity Revisited* | Showed an earlier 97.42% IMDb claim used test labels (corrected to 93.68%), and that n-gram features + RoBERTa-base add +0.13–0.15. Precedent for our ensemble. |
| Yang et al. (2019), *XLNet* | **96.80%** on IMDb (3.20% error, Table 4 of the final version; older versions and NLP-progress list 96.21%). |
| Liu et al. (2019), *RoBERTa* | The architecture behind our hub candidates. **This paper reports no IMDb result**: the often-quoted 96.54% for RoBERTa-large is a baseline from LlamBERT (2024). |

## 03_on_device_model_esp32 — the tiny model that runs on the microcontroller

| Paper | Why it's here |
|---|---|
| Weinberger et al. (2009), *Feature Hashing for Large Scale Multitask Learning* | The hashing trick: no vocabulary stored on the device, just one weight per hash bucket (256 KB at 2^18 buckets). |
| Wang & Manning (2012), *Baselines and Bigrams* (NBSVM) | Naive Bayes feature weighting; folded into the ESP32 weight table for about +1 point at no on-device cost. Also the classic strong bag-of-words baseline. |
| Joulin et al. (2016), *Bag of Tricks for Efficient Text Classification* (fastText) | Shows small n-gram models reach ~95% on Amazon/Yelp polarity with millions of training reviews. This is why more data should lift the ESP32 model. |

## 04_transformer_models — the accurate model on the hub

| Paper | Why it's here |
|---|---|
| Devlin et al. (2019), *BERT* | The base architecture everything here builds on. |
| Sanh et al. (2019), *DistilBERT* | Our current stage-2 model: 40% smaller and 60% faster than BERT. 93.51% on our IMDb test set. |
| Sun et al. (2019), *How to Fine-Tune BERT for Text Classification?* | Head + tail truncation (first 128 + last 382 tokens) used in `train_transformer.py`. 13% of IMDb reviews exceed 512 tokens. |
| Turc et al. (2019), *Well-Read Students Learn Better* | The BERT-Tiny/Mini family. Shows transformers shrunk to microcontroller size lose too much accuracy, which is why the ESP32 uses an n-gram model instead. |

## 05_cascades_and_edge_cloud_inference — the routing idea and the closest prior work

| Paper | Why it's here |
|---|---|
| Viola & Jones (2001), *Boosted Cascade of Simple Features* (link only) | Origin of the cheap-then-expensive cascade. |
| Teerapittayanon et al. (2016), *BranchyNet* | Early exit: easy inputs leave the network early. |
| Teerapittayanon et al. (2017), *Distributed DNNs over the Cloud, the Edge and End Devices* | Splitting one model across device, edge and cloud. Prior work on tiered inference. |
| Varshney & Baral (2022), *Model Cascading* | Confidence-based cascades for NLP. The closest NLP precedent for our router. |
| Huang et al. (2025), *Edge-Cloud Model Cascades via Conformal Alignment* | Edge-to-cloud deferral with statistical guarantees (images and text QA). Closest edge-cloud prior work. |
| Ratul, Guo & Yang (2025), *Cascading IDK Classifiers* | "I don't know" cascades with per-stage confidence thresholds, on a Jetson. Images, not text. |
| *Accuracy-Aware IDK Cascades* (2026) (link only) | Per-stage thresholds tuned on validation data at the edge. Images. |

## 06_learning_to_defer_and_confidence — how the chip decides it's unsure

| Paper | Why it's here |
|---|---|
| Guo et al. (2017), *On Calibration of Modern Neural Networks* | When a model's "90% confident" really means 90% right. Our router relies on this. |
| Geifman & El-Yaniv (2017), *Selective Classification for Deep Neural Networks* | Answering only when confident and abstaining otherwise. The theory behind the confidence cutoff. |
| Madras et al. (2018), *Predict Responsibly: Learning to Defer* | Introduces learning to defer: train a model to pass inputs to a downstream decision-maker. |
| Mozannar & Sontag (2020), *Consistent Estimators for Learning to Defer to an Expert* | The standard learning-to-defer loss. The basis for training the chip to predict "would the transformer fix this?" |

## 07_knowledge_distillation — a big model teaching a small one

| Paper | Why it's here |
|---|---|
| Hinton et al. (2015), *Distilling the Knowledge in a Neural Network* | Training a small model on a large model's soft predictions. |
| Tang et al. (2019), *Distilling Task-Specific Knowledge from BERT into Simple Neural Networks* | BERT → small non-transformer model for sentiment. The precedent for DistilBERT teaching the ESP32 model. |

## 08_tinyml_and_energy — microcontrollers, battery and radio costs

| Paper | Why it's here |
|---|---|
| Rajapakse et al. (2022), *Intelligence at the Extreme Edge: A Survey on Reformable TinyML* | Background on TinyML constraints and deployment. |
| Jahanbazi et al. (2026), *Energy-Aware Multi-Exit TinyML for Smart Zero-Energy Devices* | Energy-aware local-vs-offload decisions on tiny devices (person detection). Closest energy-aware prior work. |
| Raghuwanshi et al. (2026), *TinyML for On-Device and Edge Analytics in Wireless Networks* | Survey with measured on-device vs offload energy and latency trade-offs. |

## 09_earlier_approach_vader — the Review 1/2 direction we moved away from

| Paper | Why it's here |
|---|---|
| Hutto & Gilbert (2014), *VADER* | The lexicon-based scorer from the earlier TF-IDF + VADER plan (`build_deck.js`). Kept for the "what we tried before" section. |

## 10_hardware_datasheets — target devices

| Document | Why it's here |
|---|---|
| Espressif, *ESP32-S3 Series Datasheet* | 512 KB SRAM and external flash/PSRAM limits: why DistilBERT can't run on-chip. |
| Raspberry Pi, *Raspberry Pi Zero 2 W Product Brief* | $15 board, 512 MB RAM: the smallest mainstream device that fits a transformer (the hub). |

## 11_energy_cost_of_nlp — whether energy matters for language models at all

| Paper | Why it's here |
|---|---|
| Strubell et al. (2019), *Energy and Policy Considerations for Deep Learning in NLP* | Put NLP's energy cost on the map, mostly for *training* large models. |
| Schwartz et al. (2020), *Green AI* | Argues papers should report efficiency (energy, compute) alongside accuracy. Useful framing for reporting cost per review. |
| Tambe et al. (2021), *EdgeBERT* | Energy-optimised transformer *inference* on edge hardware. Shows inference energy for NLP is studied, but on custom accelerators, not $5 microcontrollers. |

## 12_robotics_and_battery_devices — the energy angle where it's most believable: robots

| Paper | Why it's here |
|---|---|
| Liu, Shi & Shin (2025), *Power-Efficient Autonomous Mobile Robots* | Measured on real robots: total power 30–90 W, and **motors are only 16.6–54.6% of it**. Computing is a major battery drain, so cutting on-robot model work saves real battery. |
| Pohland et al. (2026), *Offload or Overload* | Larger onboard GPUs "drain robot batteries several hours faster"; offloading helps but adds latency and bandwidth costs, and fleets can share compute. Exactly the trade-off our router manages. |
| Tahir et al. (2025), *Edge Computing and its Application in Robotics: A Survey* | Background on robots offloading work to edge servers, including energy-aware offloading. |
| Spezialetti, Placidi & Rossi (2020), *Emotion Recognition for Human-Robot Interaction* | Robots that read human emotion and sentiment are an established HRI goal. Motivates sentiment analysis on social and assistive robots. |

## 13_off_grid_messaging — text typed straight into a battery-powered ESP32

| Item | Why it's here |
|---|---|
| LILYGO T-Deck (link only) | ESP32-S3 handheld with a keyboard and LoRa radio running Meshtastic off-grid messaging. Text really does arrive at a battery-powered ESP32. |
| Alam et al. (2021), *HumAID* | 77k human-labelled disaster tweets with categories such as *requests or urgent needs*. A ready dataset if the project adds a crisis-message triage demo for off-grid devices. |

## 14_record_attempt_methods — methods for pushing past the published IMDb record

| Paper | Why it's here |
|---|---|
| Gururangan et al. (2020), *Don't Stop Pretraining* | Domain-adaptive pretraining (continued masked-word training on in-domain text): +0.4–0.7 on IMDb for RoBERTa-base. Likely smaller once we fine-tune on a large labelled pool. |
| Beltagy et al. (2020), *Longformer* | Long-document transformer: reads past 512 tokens (13.6% of IMDb reviews are longer). |
| Zaheer et al. (2020), *BigBird* | Another long-document transformer; alternative to Longformer. |
| He et al. (2021), *DeBERTaV3* | Strong encoder candidate for the ensemble (no published IMDb number; slow on Apple GPUs: 3.1 reviews/s at 512 tokens for the base model). |
| Clark et al. (2020), *ELECTRA* | Another strong encoder candidate for ensemble diversity. |

## 15_data_contamination — why borrowed models and LLM scores can't support a record claim

| Paper | Why it's here |
|---|---|
| Golchin & Surdeanu (2023), *Time Travel in LLMs* | Methods for detecting whether an LLM memorised a test set. |
| Golchin & Surdeanu (2023), *Data Contamination Quiz* (**preprint**) | Signs that GPT-4 saw about 82% of the IMDb test set, so zero-shot LLM scores on IMDb are not evidence. |
