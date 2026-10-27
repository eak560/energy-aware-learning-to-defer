// Builds handoff/project_handoff.docx: everything done on the project since Review 2 (22 Sep 2026), for
// whoever picks it up next. Numbers are copied from outputs/*.json, outputs/logs/ and Modal's billing report
// as of 26 Oct 2026. Render to PDF in Word (File > Save As > PDF) or with the osascript in handoff/README.md.
//   NODE_PATH=<dir with the docx package> node handoff/build_handoff.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat, Packer,
  PageNumber, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, WidthType,
} = require("docx");

const OUT = path.join(__dirname, "project_handoff.docx");
const INK = "3A2E31", MUTED = "8A7E80", ROSE = "8C4B57", SAGE = "4A5A50", BLUSH = "F7EFF1", MAUVE = "9C7F89", MINT = "E3EBE5";
const PAGE_W = 11906, MARGIN = 1134, W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

// ------------------------------------------------------------------ building blocks
const body = [];
const runs = (text, base = {}) => {
  // **bold** spans inside a string
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) => t.startsWith("**")
    ? new TextRun({ text: t.slice(2, -2), ...base, bold: true }) : new TextRun({ text: t, ...base }));
};
const P = (text, opts = {}) => body.push(new Paragraph({ spacing: { after: 140, line: 276 }, ...opts.para,
  children: runs(text, { size: 21, color: INK, ...opts.run }) }));
const H1 = (text, newPage = false) => body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: newPage,
  keepNext: true, children: [new TextRun(text)] }));
const H2 = (text) => body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun(text)] }));
const BUL = (items) => items.forEach((t) => body.push(new Paragraph({ numbering: { reference: "bullets", level: 0 },
  spacing: { after: 70, line: 264 }, children: runs(t, { size: 21, color: INK }) })));
const NUM = (items, ref) => items.forEach((t) => body.push(new Paragraph({ numbering: { reference: ref, level: 0 },
  spacing: { after: 70, line: 264 }, children: runs(t, { size: 21, color: INK }) })));
const NOTE = (text) => body.push(new Paragraph({ spacing: { before: 60, after: 160 },
  shading: { fill: MINT, type: ShadingType.CLEAR, color: "auto" }, border: { left: { style: BorderStyle.NONE, size: 0, color: "auto" } },
  indent: { left: 120, right: 120 }, children: runs(text, { size: 20, color: INK }) }));
const CODE = (lines) => lines.forEach((l, i) => body.push(new Paragraph({ spacing: { after: i === lines.length - 1 ? 160 : 0 },
  shading: { fill: "F4F1F2", type: ShadingType.CLEAR, color: "auto" }, indent: { left: 120, right: 120 },
  children: [new TextRun({ text: l, font: "Courier New", size: 17, color: INK })] })));

const border = { style: BorderStyle.SINGLE, size: 4, color: "E2D6D9" };
function TABLE(fractions, header, rows, opts = {}) {
  const widths = fractions.map((f) => Math.round((f / fractions.reduce((a, b) => a + b, 0)) * W));
  widths[widths.length - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (text, w, head, right) => new TableCell({
    borders: { top: border, bottom: border, left: border, right: border }, width: { size: w, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: { fill: head ? MAUVE : BLUSH, type: ShadingType.CLEAR, color: "auto" },
    children: [new Paragraph({ alignment: right ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(String(text), { bold: head, color: head ? "FFFFFF" : INK, size: 18 }) })],
  });
  const num = opts.num || [];
  body.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: [
    new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) => cell(h, widths[i], true, num.includes(i))) }),
    ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, widths[i], false, num.includes(i))) })),
  ] }));
  body.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
}

// ------------------------------------------------------------------ title page
body.push(new Paragraph({ spacing: { before: 2400, after: 120 }, children: [new TextRun({ text: "Project handoff", font: "Cambria", size: 60, bold: true, color: INK })] }));
body.push(new Paragraph({ spacing: { after: 360 }, children: [new TextRun({ text: "Energy-aware learning to defer for sentiment analysis on battery-powered devices", font: "Cambria", size: 30, italics: true, color: ROSE })] }));
P("**Scope:** everything done on the project since Review 2 (22 September 2026), up to 26 October 2026.");
P("**Purpose:** give anyone picking the project up the full context: what was decided, what was built and measured, every number with its source, what it cost, what was corrected along the way, where every file is, and what is still open.");
P("**Project folder:** /Volumes/Ehsan/AI Sentiment (external drive). Nothing in it is committed to git yet (see section 12).");
P("**How to read it:** section 1 is a one-page summary. Sections 2–10 go through the work in order. Section 11 lists corrections, section 12 open items, and section 13 is the reproduce-and-file map.");
body.push(new Paragraph({ spacing: { before: 600 }, children: [new TextRun({ text: "Contents", font: "Cambria", size: 26, bold: true, color: ROSE })] }));
NUM(["Summary", "Starting point: Review 2", "Timeline", "The system", "Data and leakage control (Phase 1)",
  "Models: baseline, device model, hubs (Phases 0, 2, 3)", "Record attempt on IMDb", "Learning to defer (Phases 4–5)",
  "Energy (Phase 6)", "Compute cost", "Corrections and lessons", "Open items and next steps",
  "Deliverables, files and how to rebuild"], "toc");

// ------------------------------------------------------------------ 1. summary
H1("1. Summary", true);
P("At Review 2 the plan was a single CPU model: TF-IDF + logistic regression with one extra VADER lexicon feature. That experiment was never run. The project instead became a two-tier system: a 256 KB hashed n-gram model on an ESP32-S3 microcontroller answers most reviews itself and sends only some over Wi-Fi to a transformer on a Raspberry Pi Zero 2 W hub. The research question became which reviews are worth sending: the device's own confidence (confidence routing), or a second small model trained to predict whether the hub would fix the answer (learned deferral).");
H2("Headline results");
BUL([
  "**Device model:** 256 KB of int8 weights, 92.69% on the official IMDb test set (trained on 1.94M reviews; 92.32% after the stricter second leakage clean).",
  "**Hubs:** DistilBERT 93.51% on the official 20k training reviews; retrained with 1M extra leak-free reviews, DistilBERT 95.83% and RoBERTa-base 96.72%.",
  "**Main research result (negative):** learned deferral does not beat confidence routing. Across three hubs it stays within 0.14 accuracy points at every tested send rate, and none of 15 differences survives a Bonferroni correction. Reason: stronger hubs rarely break a correct device answer (1.2–1.5% vs 3.9%), which removes learned deferral's easy win.",
  "**Energy (modelled, not measured):** with the strong hubs, sending about 8% of reviews closes half the device–hub accuracy gap at about 12× less device energy than sending every review; sending 15–17% closes three quarters at 5.8–6.5× less.",
  "**Record attempt:** an ensemble of ELECTRA-large + DeBERTa-v3-large + the 1 MB n-gram model scores 97.40% on IMDb test (95% CI 97.21–97.58%), above the best peer-reviewed 97.1%, in the extra-training-data setting.",
  "**Cost:** $20.27 of Modal cloud GPU time, itemised per run, all paid from free credits ($0 billed).",
]);
H2("Deliverables produced");
BUL([
  "IEEE conference paper, 5 pages, Word and PDF (paper/).",
  "22-slide presentation split across three presenters (Aditya slides 1–8, Danyson 9–15, Ehsan 16–22), with word-for-word speaker notes (slides/).",
  "Presenter scripts as Word, PDF, Markdown and a shared online Doc.",
  "A live laptop demo that runs the real models and shows routing and simulated energy per review (demo/).",
  "Updated ROADMAP.md (Phases 3–6 and a Phase 5 follow-up section).",
]);
H2("Most important open items");
BUL([
  "**Nothing is committed to git.** The repository has no commits; every file is untracked.",
  "**Hardware (Phase 7) is not started:** the energy numbers use datasheet currents with placeholder timings.",
  "Two small wording fixes are pending in the paper and slides, and the ROADMAP's Phase 6 energy figures should be aligned with the paper's (section 11).",
]);

// ------------------------------------------------------------------ 2. starting point
H1("2. Starting point: Review 2");
P("Review 2 (deck review2_update.pptx, dated 22 Sep 2026; presented by Ehsan Abdulkhader, Danyson Antony and Aditya Achar) proposed:");
BUL([
  "Keep the Review 1 baseline: TF-IDF unigrams + bigrams → logistic regression, CPU only.",
  "Add one feature: VADER's rule-based compound sentiment score, stacked onto the TF-IDF matrix (hybrid lexicon + ML).",
  "Rule out Jev / Open-Jev (GPU-scale models, unpublished method) as contrary to the CPU-only thesis.",
  "Results were placeholders (“TBD”); calibration was a stretch goal.",
]);
P("**What happened to that plan:** it was replaced before being run; there is no VADER code in the repository. The VADER paper is kept in papers/09_earlier_approach_vader for a “what we tried before” section. The new direction is the two-tier device + hub system in section 4.");
P("A project-update deck (slides/project_update.pptx, 19 Oct) already reported the state as of that date. Everything after 19 Oct (the retrained hubs, the paper, the final talk, the demo and the corrections) is new in this handoff, and a few figures in that deck are now out of date (section 11).");
NOTE("Team: Ehsan Abdulkhader (24BCT0089), Danyson Antony (24BAI0196) and Aditya Achar (24BCI0250), the same team as Review 2. The paper, slides and scripts all list these three.");

// ------------------------------------------------------------------ 3. timeline
H1("3. Timeline");
P("Dates come from the job logs in outputs/logs/ (time the log was last written) and from Modal's billing report.");
TABLE([1.2, 4.2], ["When", "What was done"], [
  ["22 Sep", "Review 2: TF-IDF + VADER plan presented."],
  ["19 Oct, early", "Phase 0 baseline: TF-IDF + LR (01:27), ESP32 size study (01:43), DistilBERT fine-tune (02:20), confidence cascade (02:25)."],
  ["19 Oct, morning", "Phase 1 data: Kaggle IMDb and Amazon downloads and pool builds (03:24–04:49). Phase 4 hub labels (09:45). Phase 2 device model at 1.94M reviews (09:51). Phases 5–6 on this first-round data: learned deferral vs confidence routing (level, ±0.1 pts) and the energy model (09:56)."],
  ["19 Oct, late morning", "Leakage clean round 2 after an adversarial review: test movies, test authors, near-duplicates; splits_v2 (11:01)."],
  ["19 Oct, afternoon", "Record attempt on Modal H100s: RoBERTa-large official reproduction, then RoBERTa-large, ELECTRA-large and DeBERTa-v3-large with 1M extra reviews, plus long-review predictions (12:12–15:57). n-gram models retrained on v2 data (14:05). Stacked ensemble. Project-update deck (16:19)."],
  ["25–26 Oct", "Phase 5 follow-up: hubs retrained on 1M leak-free reviews (DistilBERT, RoBERTa-base), deferral slice re-drawn, routers retrained, cascade and energy rerun, significance tests added."],
  ["26 Oct", "IEEE paper; presentation (12 then 22 slides); presenter scripts (Doc, Word, PDF); cost itemisation and correction; laptop demo; 64 KB → 128 KB router correction; this handoff."],
]);

// ------------------------------------------------------------------ 4. system
H1("4. The system");
P("**Device:** an ESP32-S3 microcontroller on battery (512 KB on-chip SRAM, about $5). It hashes the review's words and word pairs into 2^18 buckets, adds up one int8 weight per bucket (divided by √n, n = distinct buckets) and applies a sigmoid to get p(x), the probability the review is positive. Model: 262,144 int8 weights = 256 KB, plus one scale (0.3075) and one bias (0.0152). No vocabulary is stored.");
P("**Router:** a second model on the device computes g(x), the expected accuracy gain of sending the review. The device sends the review only if g(x) > λ, where λ is the price of one Wi-Fi send in accuracy. Sweeping λ traces accuracy against battery use.");
P("**Hub:** a Raspberry Pi Zero 2 W (512 MB RAM, about $15) on the same local network, running an int8 transformer (DistilBERT or RoBERTa-base). It returns the label.");
P("**Two routing rules compared:** confidence routing sends reviews with the highest 1 − max(p, 1 − p). Learned deferral is a 3-class logistic regression predicting gain = (hub right) − (device right) ∈ {−1, 0, +1} from 2^16 hashed n-gram buckets, the device's confidence (10 bins) and review length (9 bins); g(x) = P(+1) − P(−1).");
P("**Memory:** the router needs two int8 weight tables of 65,536 entries (fix and break logits relative to no change) = 128 KB. Both device models together use 384 KB of the 512 KB SRAM.");
P("**Use cases** (from the roadmap): social and assistive robots (motors are only 16.6–54.6% of measured robot power; Liu et al. 2025), off-grid messengers (Meshtastic on an ESP32-S3 LILYGO T-Deck), wearables with a phone as hub, smart toys and battery feedback kiosks.");

// ------------------------------------------------------------------ 5. data
H1("5. Data and leakage control (Phase 1)");
P("**Labels:** IMDb rating ≤ 4/10 negative, ≥ 7/10 positive (Maas et al. 2011 rule); Amazon 1–2 stars negative, 4–5 positive; middle and missing ratings dropped; Amazon titles dropped because they state the rating. **Official splits:** IMDb train 25,000 → 20,000 train + 5,000 validation (fixed seed); test 25,000, never changed, scored once per final system.");
H2("Round 1: build the pool and remove copies of the benchmark");
TABLE([3, 1.4, 1.4], ["Step", "Kaggle IMDb", "Amazon Movies & TV"], [
  ["Reviews read", "5,571,499", "17,328,314"],
  ["No usable rating", "1,384,838", "1,260,217"],
  ["Too short", "614", "3,353,755"],
  ["Duplicates within the pool", "39,243", "762,073"],
  ["Copies of official test reviews (exact / prefix / suffix)", "23,636 (22,766 / 537 / 333)", "182"],
  ["Copies of validation reviews", "4,695", "44"],
  ["Copies of training reviews", "18,745", "147"],
  ["Kept", "4,099,728 (1,135,184 neg / 2,964,544 pos)", "11,951,896"],
], { num: [1, 2] });
P("22,766 of the 25,000 official test reviews (91%) were in the public scrape word for word. Training on them would have produced a fake, too-good score.");
H2("Round 2: after an adversarial review");
TABLE([3, 1.6], ["Flag", "Reviews"], [
  ["Reviews of official test-set movies (title + year match, roman-numeral suffixes handled)", "163,409"],
  ["Reviews by any of the 16,819 authors who also wrote a test review", "635,853"],
  ["Near-duplicates sharing ≥ 30% of a val/test review's word 8-grams", "443"],
  ["Eligible IMDb reviews left (movie- and author-disjoint from test)", "3,336,925"],
], { num: [1] });
H2("Splits used");
TABLE([2.2, 1.4, 3], ["Split", "Reviews", "Use"], [
  ["v1 chip_train (round 1)", "1,920,408", "Device model v1 (with the 20k official reviews: 1.94M)"],
  ["v1 defer (round 1)", "300,000", "Deferral labels for the first-round experiments (weak hub)"],
  ["v2 chip_train (round 2)", "1,532,574", "Device model v2; the first 1,000,000 rows train the 1M hubs and record models"],
  ["v2 defer (round 2)", "300,000", "Deferral labels for the retrained hubs; verified 0 overlap with hub training"],
  ["v2 val_pool", "50,000", "Held-out 5% of movies, length-matched to test; used to pick checkpoints and ensembles"],
  ["Ablation sets", "163,298 / 599,062 / 1,253,450", "Test-movie reviews / test-author reviews / long Amazon reviews"],
], { num: [1] });
NOTE("Why the deferral slice was re-drawn: 94,194 of the 300,000 v1 deferral reviews (31%) are inside the first 1M rows of v2 chip_train, i.e. inside the retrained hubs' training data. Labels from it would have flattered the hub, so the 1M-hub experiments use the v2 slice (0 overlap, checked by hashing every review).");

// ------------------------------------------------------------------ 6. models
H1("6. Models: baseline, device model, hubs");
H2("Phase 0: baseline cascade (official 20k training reviews)");
TABLE([2.6, 1, 1, 1.2], ["System", "Test accuracy", "Sent to transformer", "Reviews/s (M3 Pro)"], [
  ["TF-IDF + logistic regression (C by 3-fold CV)", "90.28%", "0%", "6,822"],
  ["DistilBERT (2 epochs, batch 16, lr 3e-5, head 128 + tail 382 tokens)", "93.51%", "100%", "133"],
  ["Confidence cascade, τ = 0.64 (fewest sends within 0.5 pts of DistilBERT on val)", "92.50%", "10.0%", "960"],
  ["Stacked ensemble of both (upper bound)", "93.95%", "100%", "131"],
], { num: [1, 2, 3] });
P("At least one of the two models is right on 96.46% of test reviews. On validation the cascade first matches DistilBERT at 14.5% sent; its most accurate validation point is 26% sent (the ROADMAP's “matches DistilBERT at 28% sent” comes from this curve). DistilBERT trained in 47 minutes on the laptop GPU.");
H2("ESP32 feasibility (20k training reviews, validation accuracy, int8)");
TABLE([1.2, 1, 1, 1, 1], ["Hash table", "16 KB (2^14)", "64 KB (2^16)", "256 KB (2^18)", "1 MB (2^20)"], [
  ["1–2-grams, Naive Bayes weighting", "86.6%", "89.3%", "90.3%", "90.6%"],
], { num: [1, 2, 3, 4] });
P("1–3-grams were no better. Naive Bayes weighting (Wang & Manning 2012) helps at small data and is folded into the weights at no device cost. 256 KB was chosen: nearly the 1 MB accuracy at a quarter of the memory.");
H2("Phase 2: device model trained on millions of reviews");
P("Method: hashed unigrams + bigrams, binary and L2-normalised; Naive Bayes log-count ratios folded into the weights; logistic loss with averaged SGD, 5 passes in 100k-review chunks; regularisation chosen on validation; weights rounded to int8 with one float scale.");
TABLE([2, 1, 1, 1, 1, 1.1], ["Training reviews", "20k", "100k", "300k", "1M", "1.94M"], [
  ["256 KB validation accuracy", "90.18%", "91.10%", "91.82%", "92.30%", "92.76%"],
], { num: [1, 2, 3, 4, 5] });
BUL([
  "**v1 (round-1 data, 1.94M reviews):** 256 KB 92.69% test (92.76% val); Naive Bayes off 92.72% val; 1 MB 93.12% val.",
  "**Ablations:** adding reviews of test-set movies changes test accuracy by +0.02 points (leakage of that kind barely matters for this model); adding 1.25M long Amazon reviews changes it by −0.13 (Amazon was dropped).",
  "**v2 (round-2 data, 1.55M reviews):** 256 KB 92.32% test, 1 MB 92.80% test. Lower than v1 because stricter cleaning removed about 390k training reviews. v2 is the device model for all retrained-hub results and the demo.",
]);
H2("Phase 3: hubs");
TABLE([1.8, 1.2, 0.7, 0.7, 0.9, 1.2, 0.8, 0.8, 0.8], ["Hub", "Training reviews", "Epochs", "Batch", "Learning rate", "Hardware", "Val", "val_pool", "Test"], [
  ["DistilBERT, 20k", "20,000", "2", "16", "3e-5", "Laptop GPU, 47 min", "93.16%", "–", "93.51%"],
  ["DistilBERT, +1M", "1,020,000", "1", "32", "3e-5", "H100, ≈2,240/s", "95.68%", "96.05%", "95.83%"],
  ["RoBERTa-base, +1M", "1,020,000", "1", "32", "2e-5", "H100, ≈1,170/s", "96.46%", "96.80%", "96.72%"],
], { num: [1, 2, 3, 6, 7, 8] });
P("Shared recipe for the +1M runs (src/train_hub.py via src/modal_app.py): 1,020,000 ÷ 32 = 31,875 optimiser steps; AdamW, warm-up over 6% of steps then linear decay; bfloat16; length-bucketed batches; long reviews keep the first 128 and last 382 tokens; accuracy on val_pool every 2,000 steps, best checkpoint kept. RoBERTa-base reused RoBERTa-large's cached tokens (identical tokenizer), saving a tokenize run. As int8 models they should need about 67 MB and 125 MB on the Pi; RoBERTa-base needs about twice DistilBERT's compute per review (not yet measured on the Pi).");

// ------------------------------------------------------------------ 7. record
H1("7. Record attempt on IMDb");
P("Goal: test how high accuracy can honestly go with leak-free extra data. All choices (model variants, whether to read long reviews in sliding windows, ensemble members, stacker) were made on val_pool; the test set was scored once for the final ensemble.");
TABLE([2.6, 0.9, 1, 1], ["System", "Learning rate", "val_pool", "Test"], [
  ["RoBERTa-large, official 20k only (our reproduction)", "1e-5", "96.38%", "96.54%"],
  ["RoBERTa-large + 1M reviews", "1e-5", "97.24%", "97.21%"],
  ["ELECTRA-large + 1M (long reviews in sliding windows)", "1e-5", "97.37%", "97.22%"],
  ["DeBERTa-v3-large + 1M", "8e-6", "97.51%", "97.33%"],
  ["Stacked ensemble: ELECTRA + DeBERTa + 1 MB n-gram", "–", "97.54% (5-fold CV)", "97.40%"],
], { num: [1, 2, 3] });
BUL([
  "All large models: 1 epoch on 1,020,000 reviews, batch 32, bfloat16, H100; RoBERTa-large about 490 reviews/s, DeBERTa about 218/s.",
  "Stacker weights (logit scale): DeBERTa 0.577, ELECTRA 0.205, n-gram 0.042.",
  "95% bootstrap CI 97.21–97.58%; de-duplicated test (24,479 reviews): 97.40%.",
  "Exact McNemar vs best single model: 41 vs 24 discordant reviews, p = 0.046. Vs official-data RoBERTa-large: 359 vs 145, p ≈ 5.6 × 10⁻²².",
  "Reference points: ERNIE-Doc 97.1% (best peer-reviewed), XLNet 96.8%, LlamBERT 96.68% (extra data); our RoBERTa-large reproduction matches the published 96.54% baseline.",
  "**How to state it:** “97.40% on IMDb test using about 1M extra rating-labelled IMDb reviews, de-duplicated and movie- and author-disjoint from test”: an extra-training-data result, single training runs, and about 2.9% of IMDb test labels are wrong (Northcutt et al. 2021), so ~97% is the practical ceiling.",
]);

// ------------------------------------------------------------------ 8. learning to defer
H1("8. Learning to defer (Phases 4–5)");
H2("Deferral labels");
TABLE([2.4, 1, 1, 1], ["Hub, slice", "Hub fixes (+1)", "Hub breaks (−1)", "No change (0)"], [
  ["DistilBERT 20k, v1 slice (device v1)", "4.10%", "3.90%", "92.00%"],
  ["DistilBERT +1M, v2 slice (device v2)", "14,942 (4.98%)", "4,564 (1.52%)", "280,494"],
  ["RoBERTa-base +1M, v2 slice (device v2)", "16,276 (5.43%)", "3,732 (1.24%)", "279,992"],
], { num: [1, 2, 3] });
P("Router training: 250,000 reviews of the slice; regularisation C from {0.1, 0.3, 1, 3, 10} chosen by accuracy at 10% sent on the other 50,000 (C = 0.3 for the weak hub, 0.1 for the 1M hubs). A variant that sees only the confidence and length bins was also trained.");
H2("Evaluation protocol");
BUL([
  "For a target send share t, the threshold is the (1 − t) quantile of the router's scores on the 5,000 validation reviews, applied once to the 25,000 test reviews (test send shares land within 2 points of t).",
  "Also reported: the send share with the best validation accuracy.",
  "Paired comparison: exact McNemar test on the 25,000 test predictions; 5 operating points × 3 hubs = 15 tests, Bonferroni level 0.05 ÷ 15 = 0.0033.",
]);
H2("Results: test accuracy (%), confidence / learned (McNemar p)");
TABLE([1.9, 1, 1, 1, 1, 1.2], ["Hub (alone)", "5% sent", "10%", "20%", "30%", "Best rate on val"], [
  ["DistilBERT 20k (93.51)", "93.63 / 93.64 (0.94)", "94.05 / 93.92 (0.04)", "93.91 / 93.98 (0.28)", "93.81 / 93.95 (0.10)", "94.07 / 93.99 (0.22); 12% / 17% sent"],
  ["DistilBERT +1M (95.83)", "93.71 / 93.68 (0.64)", "94.70 / 94.75 (0.24)", "95.48 / 95.54 (0.07)", "95.72 / 95.72 (1.00)", "95.83 / 95.82 (0.57); 77% / 78% sent"],
  ["RoBERTa-base +1M (96.72)", "93.97 / 93.91 (0.37)", "95.14 / 95.23 (0.03)", "96.12 / 96.16 (0.28)", "96.52 / 96.52 (1.00)", "96.68 / 96.72 (0.13); 53% / 98% sent"],
]);
BUL([
  "Largest gap at any tested point: 0.14 points. The only two p < 0.05 point in opposite directions and both fail the 0.0033 bar. RoBERTa-base's +0.10 at 10% is partly a send-share effect (10.7% vs 10.5% sent; at exactly 10% the gap is +0.04).",
  "**Worked example** (RoBERTa-base, confidence, 10%): threshold = 90th percentile of validation scores = 0.255 (send if the device is under 74.5% sure) → 2,625 test reviews sent (10.50%): 832 fixed, 127 broken, 1,522 already right, 144 wrong either way → (23,079 + 832 − 127) ÷ 25,000 = 95.14%.",
  "**Why no win:** learned deferral can avoid breaks or find fixes. Strong hubs break only 1.2–1.5%, so the first lever is gone; at 10% sent, 58% of what either router sends was already right and learned deferral doesn't lower that. A perfect router reaches 97.32% at 5% sent, so the headroom is real; the device-side features just don't reveal where the hub is right.",
  "**Confidence cascade** (cascade.py, n-gram device + 1M hubs, τ within 0.5 pts of the hub on val): 95.45% at 20.0% sent (DistilBERT), 96.11% at 20.5% (RoBERTa-base).",
  "With the weak 20k hub, routing beats both models: 94.05% at 10.7% sent vs hub alone 93.51%. (An earlier “94.07% at 16%” was the maximum of the test curve, i.e. chosen on test, and is not reported.)",
]);

// ------------------------------------------------------------------ 9. energy
H1("9. Energy (Phase 6)");
P("Device energy per review, with s the share of reviews sent: E(s) = V × [I_cpu × t_local + s × (I_tx × t_tx + I_rx × t_wait)]. Idle and sleep power are excluded.");
TABLE([1.4, 1, 3], ["Parameter", "Value", "Source"], [
  ["V", "3.3 V", "ESP32-S3 datasheet v2.2"],
  ["I_cpu", "51.2 mA", "Datasheet Table 5-9: 240 MHz, one core"],
  ["I_tx", "283 mA", "Datasheet Table 5-7: 802.11n MCS7 at 18.5 dBm"],
  ["I_rx", "88 mA", "Datasheet Table 5-7: receive"],
  ["t_local", "5 ms", "Placeholder, to be measured"],
  ["t_tx", "10 ms", "Placeholder: sending ~1.5 KB on an open connection"],
  ["t_wait", "1 s", "Placeholder: radio listening while the hub answers"],
]);
P("Answering on the device: 3.3 × 0.0512 × 0.005 = 0.8448 mJ. Each send: 3.3 × (0.283 × 0.010 + 0.088 × 1.0) = 299.74 mJ. Sending everything: 300.58 mJ per review. Because the wait dominates, energy is nearly proportional to s.");
H2("Operating points chosen on validation, applied once to test (paper Table III)");
TABLE([1.9, 0.9, 0.9, 1, 1, 1], ["Hub", "Gap closed", "Sent (test)", "Test accuracy", "mJ / review", "Less than send-all"], [
  ["DistilBERT 20k", "50%", "1.2%", "92.93%", "4.3", "69.7×"],
  ["DistilBERT 20k", "75%", "2.1%", "93.14%", "7.2", "41.8×"],
  ["DistilBERT 20k", "90%", "3.4%", "93.31%", "11.1", "27.0×"],
  ["DistilBERT +1M", "50%", "8.3%", "94.41%", "25.8", "11.7×"],
  ["DistilBERT +1M", "75%", "15.0%", "95.19%", "45.9", "6.5×"],
  ["DistilBERT +1M", "90%", "26.1%", "95.68%", "79.0", "3.8×"],
  ["RoBERTa-base +1M", "50%", "8.3%", "94.76%", "25.8", "11.7×"],
  ["RoBERTa-base +1M", "75%", "16.9%", "95.89%", "51.5", "5.8×"],
  ["RoBERTa-base +1M", "90%", "25.1%", "96.36%", "76.0", "4.0×"],
], { num: [1, 2, 3, 4, 5] });
BUL([
  "Worked: RoBERTa-base, 75% of the gap. Target on validation 92.56 + 0.75 × 3.90 = 95.485% → needs 16% sent on validation → on test 16.9% sent, 95.89% → 0.8448 + 0.169 × 299.74 = 51.5 mJ → 300.58 ÷ 51.51 = 5.84×.",
  "Battery (illustrative 2,000 mAh, 3.7 V = 26,640 J): device only 31.5M reviews per charge; close 75% of the gap 517k; send everything 89k.",
  "**Scope of the old headline:** the 19 Oct claim “14–19× less energy at the transformer's accuracy” holds only for the weak 93.51% hub, which barely beats the device. With the strong hubs, fully matching the hub needs 43% (DistilBERT) or 92% (RoBERTa-base) sent on the test curve.",
]);

// ------------------------------------------------------------------ 10. cost
H1("10. Compute cost");
P("Itemised per run with “modal billing report” (run IDs matched to the log files). All paid from Modal credits; $0 billed. Every run had a hard time cap set by --max-hours. The H100 rate is $3.95 per hour.");
TABLE([3, 1, 1], ["Run", "Date", "Cost"], [
  ["DeBERTa-v3-large + 1M", "19 Oct", "$9.03"],
  ["RoBERTa-large + 1M", "19 Oct", "$3.71"],
  ["ELECTRA-large + 1M", "19 Oct", "$3.68"],
  ["RoBERTa-large, official 20k", "19 Oct", "$0.43"],
  ["Long-review predictions (3 runs)", "19 Oct", "$0.63"],
  ["Tokenising (3 runs), one run with no matching log, data upload", "19 Oct", "$0.25"],
  ["**Record attempt total**", "", "**$17.71**"],
  ["RoBERTa-base hub + 1M", "25 Oct", "$1.64"],
  ["DistilBERT hub + 1M", "25 Oct", "$0.91"],
  ["DistilBERT tokenising", "25 Oct", "$0.02"],
  ["**Retrained-hub follow-up total**", "", "**$2.56**"],
  ["**All runs**", "", "**$20.27**"],
], { num: [2] });
P("Modal's October summary shows $20.47; $0.20 is not tied to any run. The scripts assume a $30 budget, so about $9.50 of credits remain. Everything else (device models, routers, analysis, paper, slides, demo) ran free on the laptop (Apple M3 Pro, 18 GB).");

// ------------------------------------------------------------------ 11. corrections
H1("11. Corrections and lessons");
H2("Corrections made");
TABLE([2.4, 3.2], ["Issue", "Fix"], [
  ["“94.07% at 16% sent” was the best point of the test curve (chosen on test)", "Withdrawn; only validation-chosen operating points are reported"],
  ["Round-1 cleaning missed test-movie reviews, test-author reviews and near-duplicates", "Round 2 after an adversarial review; splits_v2"],
  ["31% of the v1 deferral slice was in the retrained hubs' training data", "Deferral slice re-drawn from v2; 0 overlap verified"],
  ["“14–19× less energy” presented as general", "Scoped to the weak hub; strong-hub figures from validation-chosen points"],
  ["Follow-up cost first reported as $2.76 (change in the monthly total)", "$2.56 itemised per run; ROADMAP, paper and slides updated"],
  ["Routing model called “64 KB” (one of its weight tables)", "128 KB (two tables) in paper, Fig. 1, slides, scripts, Doc and ROADMAP"],
  ["Slide claimed “largest gap at any send rate”", "“at the tested send rates” (with the weak hub the curves differ by 0.28 at 60%)"],
  ["Deck charts used hard-coded “TF-IDF” and “DistilBERT” labels for other models", "cascade.py labels outputs by model prefix"],
]);
H2("Still to correct");
BUL([
  "**“23,818 copies of validation or test reviews”** (paper, slides, scripts, ROADMAP): 23,818 is test copies only (IMDb 23,636 + Amazon 182). Validation copies (4,739) and training copies (18,892) were removed as well.",
  "**ROADMAP Phase 6 row** quotes test-curve figures (“13–14% sent closes 75% of the gap at 40–43 mJ, ~7×”); the paper and slides use the stricter validation-chosen figures (15–17% sent, 5.8–6.5×). Align the ROADMAP to the paper.",
  "**slides/project_update.pptx** (19 Oct) still shows “14–19×”, “~5% sent matches the hub” (true only for the weak hub), “23,636 copies” and “$17.99 of $30” (itemised: $17.71). Treat it as a historical snapshot.",
  "**README.md** still describes the original TF-IDF + DistilBERT cascade at the top and doesn't mention the paper, talk or demo.",
]);
H2("Engineering lessons");
BUL([
  "Public scrapes contain the benchmark: always de-duplicate against val and test, and check movies and authors, not just text.",
  "DeBERTa loaded in float16 turned every weight into NaN: force float32 when loading, then use bf16 autocast.",
  "Apple GPUs recompile per input shape: pad batches to multiples of 64.",
  "Stream large files (23M reviews) and keep token ids as flat int32 arrays to fit in 18 GB of RAM.",
  "Cache tokens on cheap CPU machines; cap every GPU run's time; checkpoint and resume.",
  "Choose everything on validation data; report confidence intervals and paired tests, and correct for multiple comparisons.",
]);

// ------------------------------------------------------------------ 12. open items
H1("12. Open items and next steps");
NUM([
  "**Commit the work to git.** The repository has no commits. .gitignore already excludes data/, outputs/models/, .npy files and node_modules; commit the code, paper, slides, demo, ROADMAP and result JSONs.",
  "**Make the slide builders self-contained.** slides/build_paper_deck.js and build_scripts_doc.js need a theme helper (apply_theme.js) and the npm packages docx, react, react-dom, react-icons and sharp, which currently live outside the repo. Copy apply_theme.js into slides/ and add the packages to package.json.",
  "**Phase 7 hardware:** ESP32-S3 firmware (tokenise, hash, int8 lookup, route), Pi Zero 2 W hub serving an int8 ONNX model over HTTP, INA219 current measurements. Replace the three placeholder timings; measure the hub's latency and int8 model sizes; decide DistilBERT vs RoBERTa-base on measured latency.",
  "**Pending text fixes** from section 11 (23,818 wording, ROADMAP Phase 6, README).",
  "**Paper details:** author emails or ORCIDs (the last author line currently shows registration numbers), acknowledgment wording, and the target conference's own requirements (page limit, copyright line in the footer).",
  "**Talk:** a timed rehearsal (the scripts assume about 130 words a minute, 24.5 minutes total); optionally a “live demo” slide in Part 4.",
  "**Research follow-ups:** richer router signals (e.g. disagreement between two small device models), repeated seeds for the record models, evaluation on corrected IMDb test labels, a second dataset with short messages.",
], "next");

// ------------------------------------------------------------------ 13. deliverables and files
H1("13. Deliverables, files and how to rebuild");
H2("Deliverables");
TABLE([2, 2.2, 2.4], ["What", "Where", "Rebuild"], [
  ["IEEE paper (5 pp, A4 template)", "paper/energy_aware_routing_ieee.docx and .pdf", "paper/make_figures.py, then paper/build_paper.py <template.docx>"],
  ["Paper figures and energy table", "paper/figures/, paper/energy_table.json", "paper/make_figures.py"],
  ["Presentation, 22 slides, 3 presenters", "slides/paper_presentation.pptx and .pdf", "slides/build_paper_deck.js (writes presenter_scripts.md too)"],
  ["Presenter scripts", "slides/presenter_scripts.docx, .pdf, .md", "slides/build_scripts_doc.js (after the deck)"],
  ["Presenter scripts, shared Doc", "https://claude.ai/artifact/HRY4ZgeDs3Yy4qtbqyAAeA", "Edited online; overview, scripts, Q&A"],
  ["Laptop demo", "demo/ (app.py, engine.py, index.html, README.md)", ".venv/bin/python -I demo/app.py → http://localhost:8770"],
  ["Roadmap and results narrative", "ROADMAP.md, README.md", "Edited by hand"],
  ["Earlier decks", "review2_update.pptx, slides/project_update.pptx", "build_deck.js, slides/build_project_update.js"],
]);
H2("Demo");
P("The demo runs the real models on the laptop: the v2 256 KB device model, the RoBERTa-base router and the RoBERTa-base +1M hub (weights downloaded to outputs/models/roberta_base_1m_best, 499 MB). For each review it shows the device's answer and the words that drove it, whether it is sent and why, the hub's answer, and the simulated energy (processing 0.84 mJ; radio transmit 9.34 mJ and receive 290.4 mJ when sent), plus session totals, reviews per charge, and a 100-test-review batch run. demo/engine.py self-checks against the paper: device predictions match exactly; confidence routing at 10% gives 95.136% (paper 95.136%); learned 95.232% (paper 95.228%, one review apart). demo/README.md has a two-minute talk track.");
H2("Key source files");
TABLE([2.2, 4], ["File", "Role"], [
  ["src/prepare_data.py, src/fast_model.py, src/train_transformer.py, src/cascade.py", "Phase 0: splits, TF-IDF + LR, DistilBERT, cascade (cascade.py now takes --fast-prefix/--bert-prefix/--tag)"],
  ["src/build_pool.py, src/maas_movies.py, src/pool_splits.py, src/pool_hygiene.py", "Phase 1: pool, test-movie list, v1 splits, round-2 cleaning and splits_v2"],
  ["src/esp32_feasibility.py, src/chip_model.py, src/ngram_v2.py", "Phase 2: size study, device model v1, v2 models (also score the v2 deferral slice and save weights)"],
  ["src/train_hub.py, src/modal_app.py, src/predict_hub.py", "Hub and record models on Modal; long-review sliding windows"],
  ["src/hub_labels.py, src/defer_router.py", "Phases 4–5: hub labels; routers, operating points, McNemar (--chip-prefix/--hub-prefix/--defer-cache/--tag)"],
  ["src/energy_curves.py", "Phase 6: energy model (--tag)"],
  ["src/ensemble.py", "Record ensemble, bootstrap CI, McNemar"],
  ["src/dashboard.py", "Live job dashboard (localhost:8765)"],
  ["outputs/*.json, outputs/logs/", "Every result and run log quoted in this handoff"],
  ["papers/ + papers/references.bib", "Every cited source, grouped by purpose, with BibTeX"],
]);
H2("Reproduce the retrained-hub results");
CODE([
  "python -m modal run --detach src/modal_app.py::train --gpu H100 --max-hours 1 \\",
  "  --args \"--model roberta-base --pool-reviews 1000000 --prefix roberta_base_1m --lr 2e-5 --batch-size 32 --accum 1\"",
  "python -m modal volume get ai-sentiment outputs/roberta_base_1m_<split>_proba.npy outputs/",
  "python -I src/ngram_v2.py",
  "python -I src/defer_router.py --chip-prefix ngram256KB --defer-cache defer_v2 --hub-prefix roberta_base_1m --tag roberta_base_1m",
  "python -I src/energy_curves.py --tag roberta_base_1m",
  "python src/cascade.py --fast-prefix ngram256KB --bert-prefix roberta_base_1m --benchmark 0 --tag roberta_base_1m",
]);
P("Earlier steps (data download, pool, device model, record attempt) are listed step by step in README.md (steps 1–20). Storage: data/ is 30 GB (16 GB raw downloads, 8.7 GB pool, 5.4 GB caches); outputs/ is 0.8 GB. Modal volume “ai-sentiment” holds the uploaded splits, token caches and every cloud checkpoint (outputs/models/*).");
H2("Where else context lives");
BUL([
  "ROADMAP.md: phase table, Phase 5 follow-up section with the full comparison table.",
  "Session hand-over note: ~/Library/Application Support/Claude/side-session-notes/local_fdf17b9b-…/phase5_followup_retrained_hub.md.",
  "papers/README.md: why each cited paper is in the project.",
]);

// ------------------------------------------------------------------ document
const doc = new Document({
  creator: "Project team", title: "Project handoff",
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] },
    { reference: "toc", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 340 } } } }] },
    { reference: "next", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 340 } } } }] },
  ] },
  styles: {
    default: { document: { run: { font: "Calibri", size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Cambria", size: 34, bold: true, color: ROSE }, paragraph: { spacing: { before: 420, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 24, bold: true, color: SAGE }, paragraph: { spacing: { before: 220, after: 90 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "Project handoff · 26 October 2026 · page ", size: 17, color: MUTED }),
      new TextRun({ children: [PageNumber.CURRENT], size: 17, color: MUTED })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
