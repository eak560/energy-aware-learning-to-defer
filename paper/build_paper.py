"""Build the IEEE conference paper (.docx) from the IEEE A4 Word template.

Keeps the template's styles, page setup, footer and numbering (headings I./A.,
"Fig. 1.", "TABLE I.", "[1]") and replaces its body with the paper below.
Figures come from paper/make_figures.py; numbers were copied from outputs/*.json.

    .venv/bin/python -I paper/make_figures.py
    .venv/bin/python -I paper/build_paper.py "/path/to/Full-Paper-Template - IEEE.docx"
"""

import json
import re
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
OUT = HERE / "energy_aware_routing_ieee.docx"
COL_TW = 4860            # one text column in twips (A4 template, 2 columns, 0.25 in gap)
FIG_EMU = int(3.35 * 914400)

# ---------------------------------------------------------------- references (IEEE style, cited order)

REFS = {
    "spezialetti": "M. Spezialetti, G. Placidi, and S. Rossi, “Emotion recognition for human-robot interaction: Recent advances and future perspectives,” *Frontiers in Robotics and AI*, vol. 7, Art. no. 532279, 2020.",
    "tdeck": "LILYGO, “T-Deck: ESP32-S3 handheld with keyboard and LoRa radio,” product listing. [Online]. Available: https://store.rokland.com/products/lilygo-t-deck-cypher-complete-edition-w-4000-or-8000-mah-battery-gps-keyboard-touchscreen",
    "liu2025": "L. Liu, W. Shi, and K. G. Shin, “Power-efficient autonomous mobile robots,” arXiv:2511.20467, 2025.",
    "pohland": "S. Pohland *et al.*, “Offload or overload: A platform measurement study of mobile robotic manipulation workloads,” arXiv:2603.18284, 2026.",
    "distilbert": "V. Sanh, L. Debut, J. Chaumond, and T. Wolf, “DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter,” arXiv:1910.01108, 2019.",
    "esp32": "Espressif Systems, “ESP32-S3 series datasheet,” v2.2. [Online]. Available: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf",
    "viola": "P. Viola and M. Jones, “Rapid object detection using a boosted cascade of simple features,” in *Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR)*, vol. 1, 2001, pp. I-511–I-518.",
    "varshney": "N. Varshney and C. Baral, “Model cascading: Towards jointly improving efficiency and accuracy of NLP systems,” arXiv:2210.05528, 2022.",
    "pizero": "Raspberry Pi Ltd, “Raspberry Pi Zero 2 W product brief.” [Online]. Available: https://pip.raspberrypi.com/documents/RP-008359-DS-raspberry-pi-zero-2-w-product-brief.pdf",
    "geifman": "Y. Geifman and R. El-Yaniv, “Selective classification for deep neural networks,” arXiv:1705.08500, 2017.",
    "guo": "C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern neural networks,” arXiv:1706.04599, 2017.",
    "madras": "D. Madras, T. Pitassi, and R. Zemel, “Predict responsibly: Improving fairness and accuracy by learning to defer,” arXiv:1711.06664, 2018.",
    "mozannar": "H. Mozannar and D. Sontag, “Consistent estimators for learning to defer to an expert,” arXiv:2006.01862, 2020.",
    "maas": "A. L. Maas, R. E. Daly, P. T. Pham, D. Huang, A. Y. Ng, and C. Potts, “Learning word vectors for sentiment analysis,” in *Proc. 49th Annu. Meeting Assoc. Computational Linguistics (ACL)*, 2011, pp. 142–150.",
    "branchynet": "S. Teerapittayanon, B. McDanel, and H. T. Kung, “BranchyNet: Fast inference via early exiting from deep neural networks,” arXiv:1709.01686, 2017.",
    "ddnn": "S. Teerapittayanon, B. McDanel, and H. T. Kung, “Distributed deep neural networks over the cloud, the edge and end devices,” arXiv:1709.01921, 2017.",
    "huang": "J. Huang, S. Park, N. Paoletti, and O. Simeone, “Reliable inference in edge-cloud model cascades via conformal alignment,” arXiv:2510.17543, 2025.",
    "rajapakse": "V. Rajapakse, I. Karunanayake, and N. Ahmed, “Intelligence at the extreme edge: A survey on reformable TinyML,” *ACM Computing Surveys*, 2023, doi: 10.1145/3583683.",
    "raghuwanshi": "P. Raghuwanshi, V. Bhatia, S. Iyer, M. Latva-aho, and O. L. A. López, “TinyML for on-device and edge analytics in wireless networks: A survey of deployments, opportunities, and concept-drift mitigation,” arXiv:2606.30843, 2026.",
    "jahanbazi": "S. Jahanbazi, M. Ashraf, L. De Strycker, J. Famaey, and O. L. A. López, “Energy-aware multi-exit TinyML for smart zero-energy devices,” arXiv:2603.08047, 2026.",
    "strubell": "E. Strubell, A. Ganesh, and A. McCallum, “Energy and policy considerations for deep learning in NLP,” arXiv:1906.02243, 2019.",
    "schwartz": "R. Schwartz, J. Dodge, N. A. Smith, and O. Etzioni, “Green AI,” arXiv:1907.10597, 2019.",
    "edgebert": "T. Tambe *et al.*, “EdgeBERT: Sentence-level energy optimizations for latency-aware multi-task NLP inference,” arXiv:2011.14203, 2021.",
    "turc": "I. Turc, M.-W. Chang, K. Lee, and K. Toutanova, “Well-read students learn better: On the importance of pre-training compact models,” arXiv:1908.08962, 2019.",
    "hashing": "K. Weinberger, A. Dasgupta, J. Attenberg, J. Langford, and A. Smola, “Feature hashing for large scale multitask learning,” arXiv:0902.2206, 2009.",
    "nbsvm": "S. Wang and C. Manning, “Baselines and bigrams: Simple, good sentiment and topic classification,” in *Proc. 50th Annu. Meeting Assoc. Computational Linguistics (ACL)*, 2012, pp. 90–94.",
    "fasttext": "A. Joulin, E. Grave, P. Bojanowski, and T. Mikolov, “Bag of tricks for efficient text classification,” arXiv:1607.01759, 2016.",
    "northcutt": "C. G. Northcutt, A. Athalye, and J. Mueller, “Pervasive label errors in test sets destabilize machine learning benchmarks,” arXiv:2103.14749, 2021.",
    "erniedoc": "S. Ding *et al.*, “ERNIE-Doc: A retrospective long-document modeling transformer,” arXiv:2012.15688, 2021.",
    "golchin": "S. Golchin and M. Surdeanu, “Data contamination quiz: A tool to detect and estimate contamination in large language models,” arXiv:2311.06233, 2025.",
    "biswas": "E. Biswas, “IMDb review dataset,” Kaggle, CC0. [Online]. Available: https://www.kaggle.com/datasets/ebiswas/imdb-review-dataset",
    "amazon": "Y. Hou *et al.*, “Bridging language and items for retrieval and recommendation,” arXiv:2403.03952, 2024.",
    "roberta": "Y. Liu *et al.*, “RoBERTa: A robustly optimized BERT pretraining approach,” arXiv:1907.11692, 2019.",
    "sun": "C. Sun, X. Qiu, Y. Xu, and X. Huang, “How to fine-tune BERT for text classification?” arXiv:1905.05583, 2019.",
    "electra": "K. Clark, M.-T. Luong, Q. V. Le, and C. D. Manning, “ELECTRA: Pre-training text encoders as discriminators rather than generators,” arXiv:2003.10555, 2020.",
    "debertav3": "P. He, J. Gao, and W. Chen, “DeBERTaV3: Improving DeBERTa using ELECTRA-style pre-training with gradient-disentangled embedding sharing,” arXiv:2111.09543, 2021.",
}

# ---------------------------------------------------------------- paper content

TITLE = "Energy-Aware Routing of Sentiment Analysis Between a Microcontroller and a Transformer Hub"

VIT = ["School of Computer Science and Engineering", "Vellore Institute of Technology", "Vellore, India"]
AUTHORS = [  # name, dept, organization, city, last line (registration number)
    ["Ehsan Abdulkhader", *VIT, "Reg. No. 24BCT0089"],
    ["Danyson Antony", *VIT, "Reg. No. 24BAI0196"],
    ["Aditya Achar", *VIT, "Reg. No. 24BCI0250"],
]

ABSTRACT = (
    "Battery-powered devices such as social robots, wearables and off-grid messengers increasingly need to "
    "understand short texts, but a transformer is far too large for a microcontroller. We study a two-tier system "
    "in which an ESP32-S3 microcontroller runs a 256 KB hashed n-gram sentiment model and sends only some reviews "
    "over Wi-Fi to a transformer on a Raspberry Pi Zero 2 W hub. We compare two ways of choosing what to send: "
    "confidence routing, which sends the reviews the device is least sure about, and learned deferral, a second "
    "128 KB model trained to predict whether the hub would correct the device. To avoid inflated results we build a "
    "leakage-controlled pool of 4.1 million IMDb reviews that is movie- and author-disjoint from the official test "
    "set, and we choose every threshold on validation data. The device model reaches 92.7 percent test accuracy, and "
    "hubs trained on one million extra reviews reach 95.8 percent (DistilBERT) and 96.7 percent (RoBERTa-base). "
    "Across three hubs, learned deferral never differs from confidence routing by more than 0.14 accuracy points at "
    "the same share of reviews sent, and no difference is statistically significant after correcting for multiple "
    "tests. A stronger hub rarely breaks a correct device answer, which removes most of the advantage learned "
    "deferral could have. With a datasheet-based energy model, sending 8 to 17 percent of reviews closes half to "
    "three quarters of the device-hub accuracy gap at 6 to 12 times less device energy than sending every review."
)
KEYWORDS = "sentiment analysis, model cascades, learning to defer, TinyML, energy-aware inference, edge computing"


def energy_rows():
    t = json.loads((HERE / "energy_table.json").read_text())
    rows = []
    for r in t["rows"]:
        rows.append([r["hub"].replace(" reviews", "").replace(",", "").replace("+", ""), f"{r['gap_share']:.0%}", f"{r['test_sent']:.1%}",
                     f"{r['test_accuracy'] * 100:.2f}", f"{r['mJ']:.1f}", f"{r['saving_vs_send_all']:.1f}×"])
    return rows, t


def body():
    erows, et = energy_rows()
    return [
        ("h1", "Introduction"),
        ("p", "Many battery-powered devices handle text or speech: social and assistive robots that react to what "
              "people say [@spezialetti], off-grid messengers on which people type straight into an ESP32-S3 "
              "[@tdeck], and wearables paired with a phone. On these devices computation is a real battery cost. "
              "Measured on mobile robots, motors account for only 16.6–54.6% of total power [@liu2025], and "
              "larger onboard accelerators drain robot batteries hours faster [@pohland]. A transformer such as "
              "DistilBERT [@distilbert] needs hundreds of megabytes, far more than the 512 KB of on-chip SRAM of an "
              "ESP32-S3 [@esp32], while a bag-of-n-grams model fits in a few hundred kilobytes but is several points "
              "less accurate."),
        ("p", "A natural design is a cascade [@viola, @varshney]: a tiny model runs on the device and hands hard inputs "
              "over a radio link to a transformer on a nearby hub, here a Raspberry Pi Zero 2 W with 512 MB of RAM "
              "[@pizero]. Every hand-off costs radio energy, so the central question is which inputs to send. The "
              "usual rule sends the inputs on which the device model is least confident [@geifman, @guo]. Learning to "
              "defer [@madras, @mozannar] suggests a better rule: train a model to predict whether the hub would "
              "actually *fix* the device's answer, so that the device stops sending inputs that the hub would also "
              "get wrong or that the device already gets right."),
        ("p", "This paper tests that idea on IMDb movie-review sentiment [@maas] under a strict evaluation protocol. "
              "Our contributions are:"),
        ("bullets", [
            "a leakage-controlled training pool of 4.1 million IMDb reviews from which copies, near-duplicates, reviews "
            "of test-set movies and reviews by test-set authors are removed, so that results on the official test set "
            "are not inflated;",
            "a microcontroller-sized sentiment model (256 KB of int8 hashed n-gram weights) that reaches 92.69% test "
            "accuracy, and transformer hubs trained on one million extra reviews that reach 95.83% (DistilBERT) and "
            "96.72% (RoBERTa-base);",
            "a controlled comparison of learned deferral against confidence routing across three hubs, with all "
            "thresholds chosen on validation data and paired significance tests on the test set. Learned deferral "
            "does not beat confidence routing, and we show why;",
            "an energy model of the device, based on datasheet currents, that turns routing curves into accuracy "
            "versus energy per review.",
        ]),

        ("h1", "Related Work"),
        ("h2", "Cascades and Edge-Cloud Inference"),
        ("p", "Cheap-then-expensive cascades go back to the Viola–Jones detector [@viola]. Early-exit networks "
              "let easy inputs leave a network early [@branchynet], and distributed networks split one model across "
              "device, edge and cloud [@ddnn]. In NLP, confidence-based cascades trade accuracy for compute "
              "[@varshney], and edge-cloud cascades with statistical guarantees have been proposed for images and "
              "question answering [@huang]. In our setting the first stage is a microcontroller with no neural "
              "network at all, and the cost to minimize is device energy rather than latency."),
        ("h2", "Selective Classification and Learning to Defer"),
        ("p", "Selective classification abstains when confidence is low [@geifman] and relies on calibrated "
              "confidences [@guo]. Learning to defer trains a rule that passes inputs to a downstream expert "
              "[@madras], with consistent surrogate losses for joint training [@mozannar]. Most work defers to a "
              "human or a large expert and trains the classifier and the rule jointly. Here the device model is "
              "fixed and the deferral model itself must fit beside it on the device, in 128 KB."),
        ("h2", "TinyML and the Energy Cost of NLP"),
        ("p", "TinyML surveys describe the memory and energy limits of microcontrollers and the trade-off between "
              "on-device processing and offloading [@rajapakse, @raghuwanshi]; energy-aware multi-exit models make "
              "local-versus-offload decisions for zero-energy devices [@jahanbazi]. NLP energy has mostly been "
              "studied for training [@strubell, @schwartz] or for transformer inference on custom accelerators "
              "[@edgebert]. Transformers shrunk to microcontroller size lose too much accuracy [@turc], which is why "
              "our device uses hashed n-grams [@hashing] with Naive Bayes feature scaling [@nbsvm], an approach that "
              "scales well with training data [@fasttext]."),
        ("h2", "IMDb Accuracy and Leakage"),
        ("p", "About 2.9% of IMDb test labels are wrong [@northcutt], so roughly 97% is a practical ceiling; the best "
              "peer-reviewed result is 97.1% [@erniedoc]. Large language models show signs of having seen the IMDb "
              "test set [@golchin], so we use none. Large scraped review collections [@biswas] contain copies of "
              "test reviews, which motivates the cleaning in Section III-B."),

        ("h1", "System and Method"),
        ("h2", "System Overview"),
        ("p", "Fig. 1 shows the system. For each review *x* the device computes its own probability of a positive "
              "review, *p*(*x*), and a deferral score *g*(*x*). It sends the review to the hub only if *g*(*x*) > "
              "λ; otherwise it answers locally. The threshold λ sets the operating point, i.e., the share "
              "of reviews sent, and in an energy-aware deployment it follows from the battery budget. Accuracy is "
              "measured offline with the exact int8 arithmetic the device runs; energy comes from the model in "
              "Section III-F, because hardware measurements are still in progress."),
        ("fig", "fig1_system.png", "System overview. The device answers locally unless the deferral score exceeds "
                                   "the threshold λ, in which case it sends the review over Wi-Fi to the hub."),
        ("h2", "Data and Leakage Control"),
        ("p", "Labels follow the IMDb rule of [@maas]: ratings of 4/10 or less are negative and 7/10 or more are "
              "positive (for Amazon, 1–2 stars and 4–5 stars). The official 25,000-review training split is "
              "divided into 20,000 training and 5,000 validation reviews with a fixed seed. The official "
              "25,000-review test split is used only to report final numbers."),
        ("p", "The extra-data pool starts from 5.5 million scraped IMDb reviews [@biswas] and 17.3 million Amazon "
              "Movies & TV reviews [@amazon], which leave 4.1 million and 12.0 million labelled, de-duplicated "
              "reviews. A first cleaning round removed 23,818 pool copies of validation or test reviews. A second "
              "round flags reviews of test-set movies (163,409, matched by title and year), all 635,853 reviews by "
              "the 16,819 authors who also wrote a test review, and 443 near-duplicates that share at least 30% of "
              "a validation or test review's word 8-grams. The remaining 3,336,925 IMDb reviews are split into a "
              "balanced training slice (1,532,574), a held-out deferral slice (300,000) and a 50,000-review "
              "*val_pool* drawn from a held-out 5% of movies, used to choose model checkpoints. Neither the device "
              "model nor any hub trains on the deferral slice; we verified that none of its reviews appear in the "
              "hub training data."),
        ("h2", "On-Device Model"),
        ("p", "The device model hashes word unigrams and bigrams into 2^{18} buckets [@hashing] with binary, "
              "L2-normalized features. Naive Bayes log-count ratios [@nbsvm] are folded into the weights, which are "
              "trained with logistic loss and averaged SGD for five epochs and then quantized to int8 with one float "
              "scale: 256 KB in total. Inference is a sum of looked-up int8 weights, so no vocabulary is stored. "
              "Regularization is chosen on validation data. We use two versions: *v1*, trained on 1.94 million "
              "reviews after the first cleaning round (92.69% test), and *v2*, trained on the 1.55 million reviews "
              "left after the second round (92.32% test). The v2 model is used with the new hubs, because its "
              "training data is disjoint from the re-drawn deferral slice."),
        ("h2", "Hub Models"),
        ("p", "The hubs are DistilBERT-base-uncased [@distilbert] and RoBERTa-base [@roberta]. Reviews longer than "
              "512 tokens keep their first 128 and last 382 tokens [@sun]. The baseline hub is DistilBERT fine-tuned "
              "for two epochs on the 20,000 official training reviews. The new hubs are fine-tuned for one epoch on "
              "those reviews plus the first 1,000,000 reviews of the training slice, with batch size 32, AdamW, peak "
              "learning rate 3×10^{−5} (DistilBERT) or 2×10^{−5} (RoBERTa-base), linear warm-up "
              "over 6% of steps, length-bucketed batches and bfloat16 mixed precision on one NVIDIA H100. The "
              "checkpoint with the best val_pool accuracy, evaluated every 2,000 steps, is kept. Both runs, with "
              "tokenization, cost USD 2.56 of cloud compute. As int8 models they should need about 67 MB and 125 MB, which "
              "fits the hub's 512 MB of RAM; RoBERTa-base needs roughly twice DistilBERT's compute per review."),
        ("h2", "Routing Rules"),
        ("p", "*Confidence routing* sends the reviews with the highest score 1 − max(*p*, 1 − *p*). "
              "*Learned deferral* uses the deferral slice, where both models' answers are known, to define the gain "
              "of sending a review:"),
        ("eq", "gain(*x*) = **1**[hub correct] − **1**[device correct],", 1),
        ("p", "which is −1, 0 or +1. A three-class logistic regression predicts the gain from features the device can compute: 2^{16} "
              "hashed n-gram buckets, the device's confidence in ten one-hot bins and the review "
              "length in nine one-hot bins. The deferral score is the expected accuracy gain of sending,"),
        ("eq", "*g*(*x*) = *P*(gain = +1 | *x*) − *P*(gain = −1 | *x*).", 2),
        ("p", "The model trains on 250,000 reviews of the deferral slice; its regularization strength is chosen from "
              "{0.1, 0.3, 1, 3, 10} by accuracy at 10% sent on the other 50,000. On the device the score needs only "
              "two int8 weight tables, the fix and break logits relative to no change, so the router takes 128 KB and "
              "the two device models together use 384 KB of the ESP32-S3's 512 KB of SRAM. A *perfect router*, which "
              "sends exactly the reviews the hub fixes, gives an upper bound."),
        ("h2", "Energy Model"),
        ("p", "The device energy per review when a share *s* of reviews is sent is"),
        ("eq", "*E*(*s*) = *V* [*I*_{cpu} *t*_{local} + *s* (*I*_{tx} *t*_{tx} + *I*_{rx} *t*_{wait})].", 3),
        ("p", "Currents come from the ESP32-S3 datasheet [@esp32]: *V* = 3.3 V, *I*_{cpu} = 51.2 mA (240 MHz, one "
              "core), *I*_{tx} = 283 mA (802.11n MCS7 at 18.5 dBm) and *I*_{rx} = 88 mA. The timings are "
              "placeholders until measured: *t*_{local} = 5 ms, *t*_{tx} = 10 ms and a hub wait *t*_{wait} = 1 s "
              "with the radio listening. This gives 0.84 mJ per review when nothing is sent and 300.6 mJ when "
              "everything is sent. Idle and sleep power are excluded. Because *t*_{wait} dominates, energy is "
              "nearly proportional to *s*, so ratios between operating points barely depend on the exact timings."),
        ("h2", "Evaluation Protocol"),
        ("p", "For a target share *t* of reviews sent, a router's threshold is the (1 − *t*) quantile of its "
              "scores on the 5,000 validation reviews and is applied unchanged to the test set, so test send shares "
              "differ slightly from *t*. We also report the send share with the highest validation accuracy. "
              "Routers are compared with an exact McNemar test on the 25,000 paired test predictions. With five "
              "operating points for each of three hubs (15 tests), the Bonferroni-corrected significance level is "
              "0.0033."),

        ("h1", "Results"),
        ("h2", "Component Models"),
        ("p", "Table I lists every model alone. More data helps the device model steadily: validation accuracy rises "
              "from 90.18% with 20,000 reviews to 92.76% with 1.94 million. Two ablations show that the device model "
              "is not inflated by leakage or helped by other domains: adding reviews of test-set movies changes test "
              "accuracy by +0.02 points, and adding 1.25 million long Amazon reviews changes it by −0.13. One "
              "million extra reviews lift DistilBERT by 2.3 points. For reference, a stacked ensemble of "
              "ELECTRA-large [@electra], DeBERTa-v3-large [@debertav3] and the 1 MB n-gram model reaches 97.40% "
              "(95% confidence interval 97.21–97.58%), above the best peer-reviewed 97.1% [@erniedoc] in the "
              "extra-training-data setting; it is far too large for the hub and serves only as an accuracy ceiling."),
        ("table", "Models Alone on the Official IMDb Test Set (25,000 Reviews)",
         [1980, 980, 900, 1000],
         ["Model", "Size", "Training reviews", "Test accuracy (%)"],
         [["TF-IDF + logistic regression", "full vocab.", "20k", "90.28"],
          ["Device v1, int8 n-grams", "256 KB", "1.94M", "92.69"],
          ["Device v2, int8 n-grams", "256 KB", "1.55M", "92.32"],
          ["Device v2, int8 n-grams", "1 MB", "1.55M", "92.80"],
          ["DistilBERT", "66M param.", "20k", "93.51"],
          ["DistilBERT", "66M param.", "1.02M", "95.83"],
          ["RoBERTa-base", "125M param.", "1.02M", "96.72"],
          ["RoBERTa-large", "355M param.", "1.02M", "97.21"],
          ["Ensemble (reference only)", "≈0.8B param.", "1.02M", "97.40"]],
         "Device v1 and v2 differ in the cleaning round of their training data (Section III-B)."),
        ("h2", "Learned Deferral Versus Confidence Routing"),
        ("p", "Table II compares the two routers at the same target share of reviews sent, with thresholds chosen on "
              "validation data, and Fig. 2 shows the full test curves. With the weak 20k-review hub, routing beats "
              "both models: confidence routing reaches 94.05% at 10.7% sent, above the hub alone (93.51%), because "
              "that hub breaks almost as many device answers as it fixes. Across all three hubs, however, learned "
              "deferral stays within −0.12 to +0.14 points of confidence routing. Only two of the 15 "
              "comparisons have *p* < 0.05, and they point in opposite directions: with the weak hub at 10% sent "
              "learned deferral is worse (−0.12, *p* = 0.04), and with RoBERTa-base at 10% sent it is better "
              "(+0.10, *p* = 0.03). Neither survives the Bonferroni correction. The RoBERTa-base difference is partly "
              "a send-share effect: its learned threshold sends 10.7% of test reviews against 10.5% for confidence "
              "routing, and at exactly 10% sent on the test curve the gap is +0.04 points. At the send share with the "
              "best validation accuracy, confidence routing is ahead with the weak hub (94.07% at 11.5% sent versus "
              "93.99% at 16.7%, *p* = 0.22); with the strong hubs validation accuracy keeps rising, so both routers "
              "send over half of all reviews and end within 0.04 points of each other. A variant of the deferral "
              "model that sees only the confidence and length bins stays within 0.07 points of confidence routing at "
              "10% sent, so the 128 KB of hashed n-gram weights add little."),
        ("table", "Test Accuracy (%) at a Target Share of Reviews Sent; Thresholds Chosen on Validation Data",
         [1440, 900, 630, 630, 630, 630],
         ["Hub (alone)", "Router", "5%", "10%", "20%", "30%"],
         [["DistilBERT, 20k (93.51)", "Confidence", "93.63", "94.05", "93.91", "93.81"],
          ["", "Learned", "93.64", "93.92", "93.98", "93.95"],
          ["", "McNemar p", "0.94", "0.04", "0.28", "0.10"],
          ["DistilBERT, +1M (95.83)", "Confidence", "93.71", "94.70", "95.48", "95.72"],
          ["", "Learned", "93.68", "94.75", "95.54", "95.72"],
          ["", "McNemar p", "0.64", "0.24", "0.07", "1.00"],
          ["RoBERTa-base, +1M (96.72)", "Confidence", "93.97", "95.14", "96.12", "96.52"],
          ["", "Learned", "93.91", "95.23", "96.16", "96.52"],
          ["", "McNemar p", "0.37", "0.03", "0.28", "1.00"]],
         "The weak hub uses device v1 and the original deferral slice; the +1M hubs use device v2 and the re-drawn slice. "
         "Test send shares are within 2 points of the target."),
        ("fig", "fig2_routing.png", "Test accuracy versus the share of reviews sent to the hub for (a) the weak "
                                    "20k-review hub and (b) RoBERTa-base trained with one million extra reviews. The "
                                    "learned deferral and confidence routing curves nearly coincide; the perfect "
                                    "router shows the headroom."),
        ("h2", "Why Learned Deferral Does Not Help"),
        ("p", "Learned deferral can beat confidence routing in two ways: by not sending reviews the hub would break, "
              "and by finding the reviews the hub would fix. On the deferral slice the weak hub fixes 4.1% of device "
              "answers but breaks 3.9%; with one million extra reviews breaks fall to 1.5% (DistilBERT) and 1.2% "
              "(RoBERTa-base), while fixes rise to 5.0% and 5.4%. A stronger hub therefore removes most of the first "
              "advantage. At 10% sent with RoBERTa-base, only 4.6–4.8% of the reviews either router sends are "
              "broken, but 58% are reviews the device already gets right; learned deferral does not reduce that "
              "share (58.2% versus 58.0%). The second advantage requires knowing which reviews the hub fixes, and "
              "the hashed n-grams carry little information about that beyond the device's own confidence. The "
              "headroom is real: a perfect router reaches 97.32% at 5% sent with either 1M-review hub, against "
              "93.68–93.97% for the practical routers."),
        ("h2", "Energy"),
        ("p", "Table III converts operating points into device energy. Each target closes a share of the device-hub "
              "gap on validation data; the corresponding threshold is then applied to test. With the 1M-review hubs, "
              f"sending 8.3% of reviews closes half the gap at {erows[3][4]} mJ per review, about 12× less than "
              "sending everything, and sending 15–17% closes three quarters at 6–7× less. The weak hub "
              "looks far cheaper (up to 70×) only because it barely beats the device. Matching a strong hub "
              "exactly is expensive: on the test curves, confidence routing first reaches the hub's accuracy at 43% "
              "sent for DistilBERT and 92% for RoBERTa-base. Fig. 3 shows the trade-off: below about 10 mJ per review "
              "all hubs perform alike because most answers come from the device, while above about 20 mJ the stronger "
              "hubs give clearly more accuracy for the same energy. Because RoBERTa-base needs roughly twice "
              "DistilBERT's hub compute, its true per-send energy will be higher once *t*_{wait} is measured."),
        ("table", "Device Energy per Review with Confidence Routing (Hub Wait 1 s); Targets Chosen on Validation Data",
         [1500, 560, 640, 720, 700, 740],
         ["Hub", "Gap closed", "Sent (test)", "Test acc. (%)", "mJ / review", "Less than send-all"],
         erows,
         f"Sending every review costs {et['send_all_mJ']:.1f} mJ; answering every review on the device costs "
         f"{et['chip_only_mJ']:.2f} mJ. Timings are placeholders until measured."),
        ("fig", "fig3_energy.png", "Test accuracy versus modelled device energy per review for confidence routing to "
                                   "each hub. The dashed line marks sending every review."),

        ("h1", "Discussion and Limitations"),
        ("p", "*Energy is modelled, not measured.* Currents come from the datasheet and the timings are placeholders; "
              "Wi-Fi association, idle and sleep power, and the hub's own power are excluded, and the hub latency and "
              "int8 model sizes on the Pi Zero 2 W are estimates. Firmware for the ESP32-S3 and measurements with an "
              "INA219 current sensor are the next step."),
        ("p", "*Leakage matters for deferral labels too.* An earlier deferral slice, drawn before the second "
              "cleaning round, shares 31% of its reviews (94,194 of 300,000) with the new hubs' training data. "
              "Labels from that slice would have made the hub look better on it than it is, so we re-drew the slice."),
        ("p", "*Statistical power is limited.* A difference of 0.1 points is 25 of the 25,000 test reviews, so "
              "small router improvements are hard to establish on IMDb; a deferral method would need a clearly "
              "larger effect to be worth its 128 KB."),
        ("p", "*Scope.* We study one dataset of long English reviews and router features that fit on the device. "
              "Richer signals, such as disagreement between two small device models, may capture which reviews the "
              "hub fixes; shorter messages, as on off-grid devices, may also behave differently."),

        ("h1", "Conclusion"),
        ("p", "We built a microcontroller-to-hub sentiment cascade under a leakage-controlled protocol and asked "
              "whether learning to defer chooses better what to send than device confidence does. It does not: across "
              "three hubs from 93.5% to 96.7% accuracy, learned deferral stays within 0.14 points of confidence "
              "routing and no difference survives correction for multiple tests. Stronger hubs rarely break device "
              "answers, which leaves only the hard problem of predicting which reviews the hub will fix. Confidence "
              "routing is therefore the practical choice for such devices: with a datasheet-based energy model, "
              "sending one review in six closes three quarters of the device-hub gap at 6–7× less device "
              "energy than sending every review. Measuring those energies on real hardware is the remaining step."),

        ("h5", "Acknowledgment"),
        ("p", "Hub and reference models were trained on Modal cloud GPUs. All code, data-cleaning steps and "
              "prediction files are in the project repository."),
        ("h5", "References"),
        ("refs",),
    ]


# ---------------------------------------------------------------- inline markup -> runs

CITE = re.compile(r"\[(@[^\]]+)\]")
TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})")
order: list[str] = []


def cite(m):
    nums = []
    for key in [k.strip().lstrip("@") for k in m.group(1).split(",")]:
        if key not in REFS:
            raise KeyError(key)
        if key not in order:
            order.append(key)
        nums.append(order.index(key) + 1)
    return ", ".join(f"[{n}]" for n in sorted(nums))


def run(text, italic=False, bold=False, va=None, size=None, font=None):
    props = ""
    if font:
        props += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if bold:
        props += "<w:b/>"
    if italic:
        props += "<w:i/><w:iCs/>"
    if size:
        props += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    if va:
        props += f'<w:vertAlign w:val="{va}"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def runs(text, **kw):
    text = CITE.sub(cite, text)
    out = []
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(run(part[2:-2], bold=True, **kw))
        elif part.startswith("*"):
            out.append(run(part[1:-1], italic=True, **kw))
        elif part.startswith("_{"):
            out.append(run(part[2:-1], va="subscript", **kw))
        elif part.startswith("^{"):
            out.append(run(part[2:-1], va="superscript", **kw))
        else:
            out.append(run(part, **kw))
    return "".join(out)


def para(style, content, ppr_extra=""):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{ppr_extra}</w:pPr>{content}</w:p>'


# ---------------------------------------------------------------- blocks

def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


images: list[tuple[str, Path]] = []


def figure(name, caption):
    path = HERE / "figures" / name
    w, h = png_size(path)
    cx, cy = FIG_EMU, int(FIG_EMU * h / w)
    rid = f"rIdImg{len(images) + 1}"
    n = len(images) + 1
    images.append((rid, path))
    drawing = (
        f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{100 + n}" name="Figure {n}"/><wp:cNvGraphicFramePr>'
        '<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
        '</wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r>')
    pic = ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr>'
           f'{drawing}</w:p>')
    return pic + para("figurecaption", runs(caption))


def table(title, widths, header, rows, note):
    assert sum(widths) <= COL_TW, (title, sum(widths))
    borders = "".join(f'<w:{s} w:val="single" w:sz="2" w:space="0" w:color="auto"/>'
                      for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)

    def cell(text, w, style, center):
        jc = '<w:jc w:val="center"/>' if center else '<w:jc w:val="left"/>'
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{jc}</w:pPr>{runs(text)}</w:p></w:tc>')

    def row(cells, style, head=False):
        trpr = "<w:trPr><w:cantSplit/><w:tblHeader/><w:jc w:val=\"center\"/></w:trPr>" if head else \
               "<w:trPr><w:cantSplit/><w:jc w:val=\"center\"/></w:trPr>"
        return "<w:tr>" + trpr + "".join(cell(c, w, style, i > 0) for i, (c, w) in enumerate(zip(cells, widths))) + "</w:tr>"

    tbl = ('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>{borders}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar>'
           f'<w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
           + row(header, "tablecolhead", head=True)
           + "".join(row(r, "tablecopy") for r in rows) + "</w:tbl>")
    head = para("tablehead", runs(title), "<w:keepNext/>")
    foot = para("tablecopy", run(note, italic=True, size=14), '<w:spacing w:before="40" w:after="160"/>')
    return head + tbl + foot


def equation(text, number):
    tabs = f'<w:tabs><w:tab w:val="clear" w:pos="2520"/><w:tab w:val="clear" w:pos="5040"/>' \
           f'<w:tab w:val="center" w:pos="{COL_TW // 2}"/><w:tab w:val="right" w:pos="{COL_TW}"/></w:tabs>'
    tab = "<w:r><w:tab/></w:r>"
    content = tab + runs(text, font="Times New Roman") + tab + run(f"({number})", font="Times New Roman")
    return para("equation", content, tabs + '<w:spacing w:before="120" w:after="120"/>')


def bullets(items):
    return "".join(para("bulletlist", runs(t)) for t in items)


def references():
    return "".join(para("references", runs(REFS[k])) for k in order)


# ---------------------------------------------------------------- front matter and sections

SECT_TITLE = ('<w:sectPr><w:footerReference w:type="first" r:id="rId8"/><w:pgSz w:w="11906" w:h="16838" w:code="9"/>'
              '<w:pgMar w:top="540" w:right="893" w:bottom="1440" w:left="893" w:header="720" w:footer="720" '
              'w:gutter="0"/><w:cols w:space="720"/><w:titlePg/><w:docGrid w:linePitch="360"/></w:sectPr>')
SECT_AUTHORS = ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="11906" w:h="16838" w:code="9"/>'
                '<w:pgMar w:top="450" w:right="893" w:bottom="1440" w:left="893" w:header="720" w:footer="720" '
                'w:gutter="0"/><w:cols w:num="{n}" w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>')
SECT_BODY = ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="11906" w:h="16838" w:code="9"/>'
             '<w:pgMar w:top="1080" w:right="907" w:bottom="1440" w:left="907" w:header="720" w:footer="720" '
             'w:gutter="0"/><w:cols w:num="2" w:space="360"/><w:docGrid w:linePitch="360"/></w:sectPr>')
SECT_END = SECT_BODY.replace('<w:cols w:num="2" w:space="360"/>', '<w:cols w:space="720"/>')


def front_matter():
    out = [para("papertitle", run(TITLE), '<w:spacing w:after="120"/>'),
           f'<w:p><w:pPr><w:pStyle w:val="Author"/><w:spacing w:before="0" w:after="160" w:line="120" '
           f'w:lineRule="auto"/>{SECT_TITLE}</w:pPr></w:p>']
    for i, lines in enumerate(AUTHORS):
        parts = ['<w:r><w:br w:type="column"/></w:r>'] if i else []  # break first, so no stray line
        for j, line in enumerate(lines):
            if j:
                parts.append("<w:r><w:br/></w:r>")
            parts.append(run(line, italic=j in (1, 2), size=18))
        out.append(para("Author", "".join(parts), '<w:spacing w:before="0" w:beforeAutospacing="0" w:after="0"/>'))
    out.append(f'<w:p><w:pPr>{SECT_AUTHORS.format(n=len(AUTHORS))}</w:pPr></w:p>')
    out.append(para("Abstract", run("Abstract", italic=True) + run("—" + ABSTRACT)))
    out.append(para("Keywords", run("Keywords—" + KEYWORDS, italic=True)))
    return "".join(out)


def render_body():
    out = []
    for block in body():
        kind = block[0]
        if kind == "h1":
            out.append(para("Heading1", run(block[1])))
        elif kind == "h2":
            out.append(para("Heading2", run(block[1])))
        elif kind == "h5":
            out.append(para("Heading5", run(block[1])))
        elif kind == "p":
            out.append(para("BodyText", runs(block[1])))
        elif kind == "bullets":
            out.append(bullets(block[1]))
        elif kind == "eq":
            out.append(equation(block[1], block[2]))
        elif kind == "fig":
            out.append(figure(block[1], block[2]))
        elif kind == "table":
            out.append(table(*block[1:]))
        elif kind == "refs":
            out.append("@@REFS@@")  # filled once every citation has been numbered
    return "".join(out)


def main():
    template = Path(sys.argv[1] if len(sys.argv) > 1 else "Full-Paper-Template - IEEE.docx")
    work = Path(tempfile.mkdtemp(prefix="ieee_"))
    with zipfile.ZipFile(template) as z:
        for info in z.infolist():
            target = (work / info.filename).resolve()
            if not str(target).startswith(str(work.resolve())):
                raise ValueError(f"unsafe path in template: {info.filename}")
            z.extract(info, work)

    doc_path = work / "word" / "document.xml"
    xml = doc_path.read_text(encoding="utf-8")
    head = xml[:xml.index("<w:body>") + len("<w:body>")]
    content = front_matter() + render_body()
    content = content.replace("@@REFS@@", references())
    last = f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/>{SECT_BODY}</w:pPr></w:p>'
    doc_path.write_text(head + content + last + SECT_END + "</w:body></w:document>", encoding="utf-8")

    media = work / "word" / "media"
    media.mkdir(exist_ok=True)
    rels_path = work / "word" / "_rels" / "document.xml.rels"
    rels = rels_path.read_text(encoding="utf-8")
    extra = ""
    for rid, path in images:
        shutil.copy(path, media / path.name)
        extra += (f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                  f'relationships/image" Target="media/{path.name}"/>')
    rels_path.write_text(rels.replace("</Relationships>", extra + "</Relationships>"), encoding="utf-8")
    ct_path = work / "[Content_Types].xml"
    ct = ct_path.read_text(encoding="utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Types ", "<Types ", 1).replace(
            "<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
    ct_path.write_text(ct, encoding="utf-8")

    core = work / "docProps" / "core.xml"
    c = core.read_text(encoding="utf-8")
    c = re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{escape(TITLE)}</dc:title>", c)
    core.write_text(c, encoding="utf-8")

    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        names = ["[Content_Types].xml"] + sorted(str(p.relative_to(work)) for p in work.rglob("*")
                                                 if p.is_file() and p.name != "[Content_Types].xml")
        for name in names:
            z.write(work / name, name)
    shutil.rmtree(work)
    unused = sorted(set(REFS) - set(order))
    print(f"wrote {OUT} ({len(order)} references, {len(images)} figures)" + (f"; unused refs: {unused}" if unused else ""))


if __name__ == "__main__":
    main()
