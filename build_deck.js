const pptxgen = require("pptxgenjs");

// Palette matched to the Review 1 deck
const MAUVE = "9C7F89";       // full-bleed background / dark cards
const MAUVE_DARK = "3A2E31";  // deep text on light bg
const SAGE = "D9E3DC";        // sage-green card fill
const SAGE_TEXT = "4A5A50";
const BLUSH = "F7EFF1";       // light pink card fill
const PINK_ACCENT = "F3A9B7"; // callout / accent pink
const PINK_ACCENT_DARK = "8C4B57";
const INK = "2E2A2C";         // body text on white
const MUTED = "8A7E80";       // captions / footers
const WHITE = "FFFFFF";
const CARD_BORDER = "E2D6D9";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 in
const PAGE_W = 13.333;
const PAGE_H = 7.5;

function pageChip(slide, num) {
  slide.addShape("ellipse", {
    x: PAGE_W - 0.75, y: 0.35, w: 0.4, h: 0.4,
    fill: { color: SAGE }, line: { type: "none" },
  });
  slide.addText(String(num), {
    x: PAGE_W - 0.75, y: 0.35, w: 0.4, h: 0.4,
    align: "center", valign: "middle",
    fontFace: "Calibri", fontSize: 12, bold: true, color: MAUVE_DARK,
    isTextBox: true, margin: 0,
  });
}

function eyebrow(slide, text, color = MUTED) {
  slide.addText(text.toUpperCase(), {
    x: 0.6, y: 0.42, w: 8, h: 0.3,
    fontFace: "Calibri", fontSize: 11, bold: true, color,
    charSpacing: 2,
    isTextBox: true, margin: 0,
  });
}

function headline(slide, text, opts = {}) {
  slide.addText(text, {
    x: 0.6, y: 0.72, w: opts.w || 11.6, h: opts.h || 0.95,
    fontFace: "Cambria", fontSize: opts.size || 30, bold: true, color: opts.color || MAUVE_DARK,
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.05,
  });
}

function footer(slide, text) {
  slide.addText(text, {
    x: 0.6, y: PAGE_H - 0.55, w: 10.5, h: 0.35,
    fontFace: "Cambria", italic: true, fontSize: 10.5, color: MUTED,
    isTextBox: true, margin: 0,
  });
}

function divider(slide, y = 1.72) {
  // thin full-width rule under header block (kept subtle; not a colored accent stripe)
  slide.addShape("line", {
    x: 0.6, y, w: PAGE_W - 1.2, h: 0,
    line: { color: CARD_BORDER, width: 1 },
  });
}

// ---------------------------------------------------------------------------
// Slide 1 — Title
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: MAUVE };

  s.addShape("roundRect", {
    x: 0.6, y: 0.55, w: 2.55, h: 0.45,
    rectRadius: 0.22,
    fill: { color: PINK_ACCENT }, line: { type: "none" },
  });
  s.addText("UPDATE", {
    x: 0.6, y: 0.55, w: 2.55, h: 0.45,
    align: "center", valign: "middle",
    fontFace: "Calibri", fontSize: 12, bold: true, color: PINK_ACCENT_DARK,
    charSpacing: 2, isTextBox: true, margin: 0,
  });

  s.addText("Review 1 → Review 2 Update", {
    x: 0.6, y: 2.2, w: 11.6, h: 1.9,
    fontFace: "Cambria", fontSize: 44, bold: true, color: WHITE,
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.05,
  });

  s.addText("Sentiment Analysis of Text Reviews Using Machine Learning", {
    x: 0.6, y: 3.95, w: 10.5, h: 0.5,
    fontFace: "Cambria", italic: true, fontSize: 17, color: "EAD9DE",
    isTextBox: true, margin: 0,
  });

  s.addShape("line", {
    x: 0.6, y: 4.7, w: 2.6, h: 0,
    line: { color: PINK_ACCENT, width: 2 },
  });

  s.addText("Ehsan Abdulkhader 24BCT0089  ·  Danyson Antony 24BAI0196  ·  Aditya Achar 24BCI0250", {
    x: 0.6, y: 5.35, w: 10.8, h: 0.4,
    fontFace: "Calibri", fontSize: 12.5, bold: true, color: "F0E4E7",
    isTextBox: true, margin: 0,
  });
}

// ---------------------------------------------------------------------------
// Slide 2 — Recap
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 2);
  eyebrow(s, "Recap");
  headline(s, "Review 1 set a CPU-only, interpretable baseline");
  divider(s);

  const cards = [
    { t: "Pipeline", d: "TF-IDF (uni + bigrams) → Logistic Regression, trained on raw review text." },
    { t: "Efficient", d: "Runs entirely on CPU — no GPU, trains in minutes on a laptop." },
    { t: "Interpretable", d: "Model coefficients expose the exact words driving each prediction." },
    { t: "Negation-aware", d: "Bigram features let the model learn phrases like “not good” from data, not a dictionary." },
  ];
  const cardW = 2.68, gap = 0.22, startX = 0.6, y = 2.15, h = 3.55;
  cards.forEach((c, i) => {
    const x = startX + i * (cardW + gap);
    s.addShape("roundRect", {
      x, y, w: cardW, h, rectRadius: 0.08,
      fill: { color: i % 2 === 0 ? BLUSH : SAGE }, line: { type: "none" },
      shadow: { type: "outer", color: "9C8189", opacity: 0.18, blur: 6, offset: 2, angle: 90 },
    });
    s.addText(c.t, {
      x: x + 0.22, y: y + 0.28, w: cardW - 0.44, h: 0.6,
      fontFace: "Cambria", bold: true, fontSize: 16, color: MAUVE_DARK,
      isTextBox: true, margin: 0,
    });
    s.addText(c.d, {
      x: x + 0.22, y: y + 0.95, w: cardW - 0.44, h: h - 1.2,
      fontFace: "Calibri", fontSize: 12, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
  });

  footer(s, "Baseline architecture and results as presented in Review 1.");
}

// ---------------------------------------------------------------------------
// Slide 3 — What we investigated (Jev / Open-Jev)
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 3);
  eyebrow(s, "What we investigated");
  headline(s, "We evaluated Jev / Open-Jev as an extension — and ruled it out", { size: 27 });
  divider(s);

  const rows = [
    ["Criterion", "Jev / Open-Jev", "Our approach"],
    ["Compute", "GPU-class inference (2B–27B param models)", "CPU-only"],
    ["Maturity", "Days old, unpublished method", "Established, peer-citable (scikit-learn)"],
    ["Scale fit", "Hundreds of ms–sec per request on CPU", "Thousands of reviews / sec"],
    ["Fits our thesis", "No", "Yes"],
  ];
  s.addTable(rows, {
    x: 0.6, y: 2.05, w: 8.05, h: 3.3,
    colW: [2.1, 3.0, 2.95],
    border: { type: "solid", color: CARD_BORDER, pt: 1 },
    autoPage: false,
    fontFace: "Calibri",
    fontSize: 12,
    rowH: 0.66,
    valign: "middle",
    fill: { color: WHITE },
    color: INK,
  });
  // restyle header row
  s.addShape("rect", { x: 0.6, y: 2.05, w: 8.05, h: 0.66, fill: { color: MAUVE }, line: { type: "none" } });
  s.addText([
    { text: "Criterion", options: { bold: true, color: WHITE, breakLine: false } },
  ], { x: 0.72, y: 2.05, w: 1.98, h: 0.66, align: "left", valign: "middle", fontFace: "Calibri", fontSize: 12, isTextBox: true, margin: 0 });
  s.addText("Jev / Open-Jev", { x: 2.82, y: 2.05, w: 2.88, h: 0.66, align: "left", valign: "middle", fontFace: "Calibri", fontSize: 12, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("Our approach", { x: 5.82, y: 2.05, w: 2.83, h: 0.66, align: "left", valign: "middle", fontFace: "Calibri", fontSize: 12, bold: true, color: WHITE, isTextBox: true, margin: 0 });

  // Conclusion callout card
  s.addShape("roundRect", {
    x: 8.95, y: 2.05, w: 3.78, h: 3.3, rectRadius: 0.08,
    fill: { color: PINK_ACCENT }, line: { type: "none" },
  });
  s.addText("Conclusion", {
    x: 9.2, y: 2.3, w: 3.3, h: 0.4,
    fontFace: "Calibri", fontSize: 12, bold: true, color: PINK_ACCENT_DARK, charSpacing: 1,
    isTextBox: true, margin: 0,
  });
  s.addText("Ruled out — contradicts the project’s CPU-only, lightweight, at-scale thesis.", {
    x: 9.2, y: 2.75, w: 3.3, h: 2.4,
    fontFace: "Cambria", fontSize: 16, bold: true, color: "5A2430",
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
  });

  footer(s, "Jev: TypeSafe AI (Sept 2026, unpublished). Open-Jev: independent Qwen3.5-based reimplementation.");
}

// ---------------------------------------------------------------------------
// Slide 4 — What's new (hybrid direction)
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 4);
  eyebrow(s, "What's new");
  headline(s, "A hybrid lexicon + ML feature tests our own literature review", { size: 26 });
  divider(s);

  s.addShape("roundRect", {
    x: 0.6, y: 2.05, w: 7.1, h: 3.5, rectRadius: 0.08,
    fill: { color: SAGE }, line: { type: "none" },
  });
  s.addText("The idea", {
    x: 0.9, y: 2.3, w: 6.5, h: 0.4,
    fontFace: "Calibri", fontSize: 12, bold: true, color: SAGE_TEXT, charSpacing: 1,
    isTextBox: true, margin: 0,
  });
  s.addText(
    "Add VADER’s rule-based compound sentiment score as one extra numeric feature alongside the existing TF-IDF matrix — both feed into the same Logistic Regression model.",
    {
      x: 0.9, y: 2.75, w: 6.5, h: 1.3,
      fontFace: "Cambria", fontSize: 16, color: MAUVE_DARK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.2,
    }
  );
  s.addText(
    "Review 1’s literature slide framed rule-based (VADER) and ML (TF-IDF+LR) as two competing extremes. This experiment combines them directly instead of just citing the contrast.",
    {
      x: 0.9, y: 4.15, w: 6.5, h: 1.2,
      fontFace: "Calibri", fontSize: 13, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.25,
    }
  );

  // right-side stat callouts
  const stats = [
    { n: "+1", label: "new numeric feature\n(VADER compound score)" },
    { n: "0", label: "extra GPU / infra\nrequirements" },
  ];
  stats.forEach((st, i) => {
    const y = 2.05 + i * 1.75;
    s.addShape("roundRect", {
      x: 7.95, y, w: 4.78, h: 1.55, rectRadius: 0.08,
      fill: { color: BLUSH }, line: { type: "none" },
    });
    s.addText(st.n, {
      x: 8.2, y: y + 0.15, w: 1.5, h: 1.1,
      fontFace: "Cambria", bold: true, fontSize: 40, color: PINK_ACCENT_DARK,
      isTextBox: true, margin: 0, valign: "middle",
    });
    s.addText(st.label, {
      x: 9.6, y: y + 0.15, w: 3.0, h: 1.25,
      fontFace: "Calibri", fontSize: 12.5, color: INK,
      isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.15,
    });
  });

  footer(s, "Hutto & Gilbert (2014) — VADER; combined here with the Review 1 TF-IDF + Logistic Regression pipeline.");
}

// ---------------------------------------------------------------------------
// Slide 5 — Methodology update (pipeline diagram)
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 5);
  eyebrow(s, "Methodology update");
  headline(s, "VADER joins the TF-IDF branch before the classifier", { size: 27 });
  divider(s);

  const boxY = 3.0, boxH = 1.0, boxW = 1.95, gap = 0.55;
  const startX = 0.6;

  function box(x, y, w, h, fill, title, sub, textColor = MAUVE_DARK) {
    s.addShape("roundRect", {
      x, y, w, h, rectRadius: 0.07,
      fill: { color: fill }, line: { type: "none" },
    });
    s.addText(title, {
      x: x + 0.12, y: y + 0.1, w: w - 0.24, h: h * 0.5,
      fontFace: "Cambria", bold: true, fontSize: 13, color: textColor,
      isTextBox: true, margin: 0, valign: "top",
    });
    s.addText(sub, {
      x: x + 0.12, y: y + h * 0.52, w: w - 0.24, h: h * 0.42,
      fontFace: "Calibri", fontSize: 9.5, color: textColor,
      isTextBox: true, margin: 0, valign: "top",
    });
  }

  function arrow(x, y) {
    s.addText("→", { x, y: y - 0.05, w: 0.5, h: boxH, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 20, color: MUTED, isTextBox: true, margin: 0 });
  }

  // main row: Text reviews -> Preprocess -> [merge] -> Logistic Regression -> Sentiment
  let x = startX;
  box(x, boxY, boxW, boxH, SAGE, "Text reviews", "Raw feedback");
  x += boxW; arrow(x, boxY); x += gap;
  box(x, boxY, boxW, boxH, BLUSH, "Preprocess", "Clean, keep negation");
  x += boxW; arrow(x, boxY); x += gap;

  // merge point: two small stacked boxes feeding one arrow
  const mergeX = x;
  box(mergeX, boxY - 0.62, boxW, 0.55, BLUSH, "TF-IDF", "Uni + bigrams", MAUVE_DARK);
  box(mergeX, boxY + 0.62, boxW, 0.55, PINK_ACCENT, "VADER score", "Compound polarity", "5A2430");
  // connector lines from both into the arrow
  s.addShape("line", { x: mergeX + boxW, y: boxY - 0.35, w: gap * 0.5, h: 0.35 + 0.05, line: { color: MUTED, width: 1.25 } });
  s.addShape("line", { x: mergeX + boxW, y: boxY + boxH, w: gap * 0.5, h: -(0.35), line: { color: MUTED, width: 1.25 } });
  x += boxW + gap * 0.5;
  s.addText("→", { x, y: boxY - 0.05, w: 0.5, h: boxH, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 20, color: MUTED, isTextBox: true, margin: 0 });
  x += gap * 0.5 + 0.1;

  box(x, boxY, boxW + 0.3, boxH, SAGE, "Logistic Regression", "Trained on hybrid features");
  x += boxW + 0.3; arrow(x, boxY); x += gap;
  box(x, boxY, boxW, boxH, MAUVE, "Sentiment", "Label + confidence", WHITE);

  // small labels for merge branches
  s.addText("feature fusion (hstack)", {
    x: mergeX - 0.05, y: boxY + boxH * 0.5 - 0.02, w: boxW + 0.7, h: 0.3,
    fontFace: "Calibri", italic: true, fontSize: 9.5, color: MUTED,
    isTextBox: true, margin: 0, align: "center",
  });

  footer(s, "Dataset: Maas et al. (2011); VADER: Hutto & Gilbert (2014); implementation: scikit-learn.");
}

// ---------------------------------------------------------------------------
// Slide 6 — Results placeholder
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 6);
  eyebrow(s, "Expected results");
  headline(s, "Baseline vs. hybrid — comparison pending", { size: 30 });
  divider(s);

  const rows = [
    ["Metric", "TF-IDF + LR (baseline)", "TF-IDF + VADER + LR (hybrid)"],
    ["Accuracy", "TBD — pending experiment", "TBD — pending experiment"],
    ["F1-score", "TBD — pending experiment", "TBD — pending experiment"],
    ["VADER coefficient weight", "—", "TBD — pending experiment"],
  ];
  s.addShape("rect", { x: 0.6, y: 2.15, w: 12.1, h: 0.66, fill: { color: MAUVE }, line: { type: "none" } });
  s.addText("Metric", { x: 0.85, y: 2.15, w: 3.4, h: 0.66, valign: "middle", fontFace: "Calibri", fontSize: 12.5, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("TF-IDF + LR (baseline)", { x: 4.35, y: 2.15, w: 4.1, h: 0.66, valign: "middle", fontFace: "Calibri", fontSize: 12.5, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("TF-IDF + VADER + LR (hybrid)", { x: 8.55, y: 2.15, w: 4.15, h: 0.66, valign: "middle", fontFace: "Calibri", fontSize: 12.5, bold: true, color: WHITE, isTextBox: true, margin: 0 });

  const dataRows = rows.slice(1);
  const rowH = 0.75;
  dataRows.forEach((r, i) => {
    const y = 2.81 + i * rowH;
    s.addShape("rect", { x: 0.6, y, w: 12.1, h: rowH, fill: { color: i % 2 === 0 ? BLUSH : WHITE }, line: { color: CARD_BORDER, width: 0.75 } });
    s.addText(r[0], { x: 0.85, y, w: 3.4, h: rowH, valign: "middle", fontFace: "Calibri", fontSize: 12, bold: true, color: MAUVE_DARK, isTextBox: true, margin: 0 });
    s.addText(r[1], { x: 4.35, y, w: 4.1, h: rowH, valign: "middle", fontFace: "Calibri", italic: true, fontSize: 12, color: MUTED, isTextBox: true, margin: 0 });
    s.addText(r[2], { x: 8.55, y, w: 4.15, h: rowH, valign: "middle", fontFace: "Calibri", italic: true, fontSize: 12, color: MUTED, isTextBox: true, margin: 0 });
  });

  s.addText("Placeholder — to be filled in after running the experiment. No results have been fabricated.", {
    x: 0.6, y: 2.81 + dataRows.length * rowH + 0.25, w: 11.5, h: 0.4,
    fontFace: "Calibri", italic: true, fontSize: 11.5, color: PINK_ACCENT_DARK,
    isTextBox: true, margin: 0,
  });

  footer(s, "Comparison will report accuracy, F1-score, and the learned weight on the VADER feature.");
}

// ---------------------------------------------------------------------------
// Slide 7 — Roadmap / timeline
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 7);
  eyebrow(s, "Roadmap");
  headline(s, "Six steps from here to Review 2", { size: 30 });
  divider(s);

  const steps = [
    ["1", "Data prep", "VADER compound score per review"],
    ["2", "Feature fusion", "Concatenate score onto TF-IDF (hstack)"],
    ["3", "Train & compare", "Hybrid vs. baseline: accuracy, F1, confusion matrix"],
    ["4", "Interpret", "Read the learned VADER coefficient; update top-words table"],
    ["5", "Stretch: calibration", "Platt / isotonic scaling + reliability diagram"],
    ["6", "Write-up", "Document results, prepare Review 2 materials"],
  ];

  // timeline rail
  const railY = 2.35;
  s.addShape("line", { x: 0.9, y: railY, w: 10.6, h: 0, line: { color: CARD_BORDER, width: 2 } });

  const n = steps.length;
  const spanW = 10.6;
  steps.forEach((st, i) => {
    const cx = 0.9 + (spanW / (n - 1)) * i;
    s.addShape("ellipse", { x: cx - 0.14, y: railY - 0.14, w: 0.28, h: 0.28, fill: { color: i === n - 1 ? PINK_ACCENT : MAUVE }, line: { type: "none" } });
  });

  s.addShape("roundRect", { x: 10.85, y: railY - 0.3, w: 1.85, h: 0.6, rectRadius: 0.3, fill: { color: PINK_ACCENT }, line: { type: "none" } });
  s.addText("REVIEW 2", { x: 10.85, y: railY - 0.3, w: 1.85, h: 0.6, align: "center", valign: "middle", fontFace: "Calibri", bold: true, fontSize: 11, color: PINK_ACCENT_DARK, charSpacing: 1, isTextBox: true, margin: 0 });

  const cardY = 2.75, cardH = 3.7;
  const colW = 12.1 / 6;
  steps.forEach((st, i) => {
    const x = 0.6 + i * colW;
    s.addShape("roundRect", {
      x: x + 0.08, y: cardY, w: colW - 0.16, h: cardH, rectRadius: 0.08,
      fill: { color: i % 2 === 0 ? SAGE : BLUSH }, line: { type: "none" },
    });
    s.addShape("ellipse", { x: x + 0.28, y: cardY + 0.25, w: 0.5, h: 0.5, fill: { color: MAUVE }, line: { type: "none" } });
    s.addText(st[0], { x: x + 0.28, y: cardY + 0.25, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: "Cambria", bold: true, fontSize: 16, color: WHITE, isTextBox: true, margin: 0 });
    s.addText(st[1], {
      x: x + 0.22, y: cardY + 0.95, w: colW - 0.5, h: 0.75,
      fontFace: "Cambria", bold: true, fontSize: 13, color: MAUVE_DARK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.05,
    });
    s.addText(st[2], {
      x: x + 0.22, y: cardY + 1.75, w: colW - 0.5, h: cardH - 1.95,
      fontFace: "Calibri", fontSize: 10.5, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
  });

  footer(s, "Calibration (step 5) is a stretch goal, pursued only if time permits.");
}

// ---------------------------------------------------------------------------
// Slide 8 — Risks & limitations
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  pageChip(s, 8);
  eyebrow(s, "Risks & limitations");
  headline(s, "The hybrid approach carries its own caveats", { size: 30 });
  divider(s);

  const risks = [
    { t: "Lexicon bias", d: "VADER’s own blind spots (sarcasm, domain-specific slang) get inherited by the hybrid feature, not eliminated." },
    { t: "Feature redundancy", d: "The VADER score may overlap heavily with signal the TF-IDF n-grams already capture, limiting any accuracy gain." },
    { t: "Calibration scope", d: "Probability calibration is a stretch goal only — pursued if time allows after the core hybrid comparison is complete." },
  ];

  const cardW = 3.85, gap = 0.28, startX = 0.6, y = 2.15, h = 3.7;
  risks.forEach((r, i) => {
    const x = startX + i * (cardW + gap);
    s.addShape("roundRect", {
      x, y, w: cardW, h, rectRadius: 0.08,
      fill: { color: WHITE }, line: { color: CARD_BORDER, width: 1 },
      shadow: { type: "outer", color: "9C8189", opacity: 0.12, blur: 5, offset: 2, angle: 90 },
    });
    s.addShape("roundRect", {
      x: x + 0.28, y: y + 0.3, w: 0.55, h: 0.55, rectRadius: 0.1,
      fill: { color: PINK_ACCENT }, line: { type: "none" },
    });
    s.addText("!", {
      x: x + 0.28, y: y + 0.3, w: 0.55, h: 0.55, align: "center", valign: "middle",
      fontFace: "Cambria", bold: true, fontSize: 20, color: "5A2430",
      isTextBox: true, margin: 0,
    });
    s.addText(r.t, {
      x: x + 0.28, y: y + 1.05, w: cardW - 0.56, h: 0.5,
      fontFace: "Cambria", bold: true, fontSize: 15, color: MAUVE_DARK,
      isTextBox: true, margin: 0,
    });
    s.addText(r.d, {
      x: x + 0.28, y: y + 1.6, w: cardW - 0.56, h: h - 1.85,
      fontFace: "Calibri", fontSize: 12, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.25,
    });
  });

  footer(s, "These limitations will be reassessed once the hybrid vs. baseline comparison is run.");
}

// ---------------------------------------------------------------------------
// Slide 9 — Next steps / ask
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: MAUVE };

  s.addText("NEXT STEPS", {
    x: 0.6, y: 0.55, w: 6, h: 0.35,
    fontFace: "Calibri", fontSize: 12, bold: true, color: "EAD9DE", charSpacing: 2,
    isTextBox: true, margin: 0,
  });

  s.addText("What happens before Review 2", {
    x: 0.6, y: 1.0, w: 11.5, h: 0.9,
    fontFace: "Cambria", bold: true, fontSize: 32, color: WHITE,
    isTextBox: true, margin: 0,
  });

  const items = [
    "Implement VADER scoring and fuse it with the existing TF-IDF matrix.",
    "Train and evaluate the hybrid model against the Review 1 baseline (accuracy, F1, coefficients).",
    "If time permits, add probability calibration and a reliability diagram.",
    "Prepare Review 2 materials with real results in place of today’s placeholders.",
  ];
  let y = 2.25;
  items.forEach((it) => {
    s.addShape("ellipse", { x: 0.6, y: y + 0.06, w: 0.14, h: 0.14, fill: { color: PINK_ACCENT }, line: { type: "none" } });
    s.addText(it, {
      x: 0.95, y, w: 10.6, h: 0.55,
      fontFace: "Calibri", fontSize: 15, color: "F5EBEE",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
    y += 0.72;
  });

  s.addShape("line", { x: 0.6, y: y + 0.15, w: 2.6, h: 0, line: { color: PINK_ACCENT, width: 2 } });

  s.addText("Feedback on this direction — especially the hybrid feature choice — is welcome before we start implementation.", {
    x: 0.6, y: y + 0.4, w: 10.8, h: 0.7,
    fontFace: "Cambria", italic: true, fontSize: 14, color: "EAD9DE",
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.2,
  });
}

pres.writeFile({ fileName: "review2_update.pptx" }).then(() => {
  console.log("Wrote review2_update.pptx");
});
