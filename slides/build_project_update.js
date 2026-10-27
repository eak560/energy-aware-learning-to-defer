// Builds slides/project_update.pptx: the full project update deck.
// Palette and fonts continue the Review 1/2 decks (mauve, sage, blush; Cambria + Calibri).
//   node slides/build_project_update.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const SKILL = process.env.PPTX_SKILL_DIR;
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));
const DEPS = process.env.ICON_DEPS_DIR;
const need = (m) => require(require.resolve(m, { paths: [DEPS] }));
const React = need("react");
const ReactDOMServer = need("react-dom/server");
const sharp = need("sharp");
const fa = need("react-icons/fa");

const DATA = JSON.parse(fs.readFileSync(process.env.DECK_DATA, "utf8"));
const OUT = path.join(__dirname, "project_update.pptx");

const THEME = {
  name: "Sentiment Edge",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "2E2A2C", lt1: "FFFFFF", dk2: "3A2E31", lt2: "F7EFF1",
    accent1: "9C7F89", accent2: "8C4B57", accent3: "4A5A50", accent4: "D9E3DC",
    accent5: "F3A9B7", accent6: "8A7E80", hlink: "8C4B57", folHlink: "9C7F89",
  },
};
const HEX = { grid: "E2D6D9", axis: "8A7E80", ink: "3A2E31", mauve: "9C7F89", rose: "8C4B57",
  sage: "4A5A50", muted: "B9AEB1", pink: "F3A9B7" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Energy-Aware Hybrid Sentiment Analysis: Project Update";
pres.author = "Ehsan Abdulkhader, Danyson Antony, Aditya Achar";
const C = pres.SchemeColor;
const W = 13.333;

// ------------------------------------------------------------------ layouts
// Slide-number badge: a sage circle image (slide layouts cannot hold ellipse shapes).
const CIRCLE = "image/png;base64," + require("child_process").execFileSync(process.execPath, ["-e",
  `const sharp=require(${JSON.stringify(require.resolve("sharp", { paths: [DEPS] }))});` +
  `sharp(Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><circle cx="64" cy="64" r="64" fill="#D9E3DC"/></svg>')).png().toBuffer().then(b=>process.stdout.write(b.toString("base64")))`]).toString();
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.05, w: 11.8, h: 1.75, fontSize: 44,
      bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.6, y: 3.95, w: 11.0, h: 0.6, fontSize: 18,
      italic: true, color: C.background2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "names", type: "body", x: 0.6, y: 5.35, w: 11.6, h: 0.45, fontSize: 14,
      bold: true, color: C.background2, margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { image: { x: 12.33, y: 0.38, w: 0.42, h: 0.42, data: CIRCLE } },
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.4, w: 10.5, h: 0.32, fontSize: 12,
      bold: true, color: C.accent6, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.74, w: 11.4, h: 0.9, fontSize: 30,
      bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "footer", type: "body", x: 0.6, y: 6.95, w: 11.5, h: 0.34, fontSize: 10.5,
      italic: true, color: C.accent6, margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.33, y: 0.38, w: 0.42, h: 0.42, fontSize: 12, color: HEX.ink, align: "center", valign: "middle" },
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.55, w: 8, h: 0.35, fontSize: 12,
      bold: true, color: C.background2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.95, w: 11.6, h: 0.9, fontSize: 34,
      bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});

// ------------------------------------------------------------------ helpers
async function icon(name, color = "#FFFFFF") {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(fa[name], { color, size: 256 }));
  const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
const shadow = () => ({ type: "outer", color: "9C8189", opacity: 0.16, blur: 6, offset: 2, angle: 90 });
const T = (o) => ({ isTextBox: true, margin: 0, ...o });
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  legendFontFace: "+mn-lt", catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
  catAxisLabelColor: HEX.ink, valAxisLabelColor: HEX.axis, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  dataLabelFontSize: 11, dataLabelColor: HEX.ink, valGridLine: { color: HEX.grid, size: 0.75 },
  catGridLine: { style: "none" }, catAxisLineShow: false, valAxisLineShow: false };

function content(section, eyebrow, title, footer) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(eyebrow.toUpperCase(), { placeholder: "eyebrow", charSpacing: 2, bullet: false });
  s.addText(title, { placeholder: "title" });
  if (footer) s.addText(footer, { placeholder: "footer", bullet: false });
  return s;
}

function card(s, x, y, w, h, fill, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill },
    line: { type: "none" }, shadow: shadow(), objectName: name });
}

async function iconCircle(s, x, y, d, iconName, fill = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } });
  const pad = d * 0.25;
  s.addImage({ data: await icon(iconName), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}

async function statCard(s, x, y, w, h, fill, big, label, small, bigColor = C.accent2, iconName = null) {
  card(s, x, y, w, h, fill, `stat ${big}`);
  if (iconName) await iconCircle(s, x + 0.3, y + 0.32, 0.78, iconName, bigColor);
  s.addText(big, T({ x: x + 0.3, y: y + 1.3, w: w - 0.6, h: 1.05, fontFace: "Cambria", fontSize: 48, bold: true,
    color: bigColor, valign: "middle" }));
  s.addText(label, T({ x: x + 0.3, y: y + 2.45, w: w - 0.6, h: 0.95, fontSize: 17, bold: true, color: C.text2,
    valign: "top" }));
  if (small) s.addText(small, T({ x: x + 0.3, y: y + h - 0.75, w: w - 0.6, h: 0.5, fontSize: 12, color: C.accent6,
    valign: "bottom" }));
}

// ------------------------------------------------------------------ slides
async function build() {
  // 1. Title
  pres.addSection({ title: "Overview" });
  {
    const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Overview" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 0.6, w: 2.7, h: 0.45, rectRadius: 0.22,
      fill: { color: C.accent5 }, line: { type: "none" } });
    s.addText("PROJECT UPDATE", T({ x: 0.6, y: 0.6, w: 2.7, h: 0.45, align: "center", valign: "middle",
      fontSize: 12, bold: true, color: C.accent2, charSpacing: 2 }));
    s.addText("Energy-Aware Hybrid Sentiment Analysis", { placeholder: "title" });
    s.addText("Sentiment Analysis of Text Reviews Using Machine Learning: from a $5 chip to a record-setting ensemble",
      { placeholder: "subtitle", bullet: false });
    s.addText("Ehsan Abdulkhader 24BCT0089  ·  Danyson Antony 24BAI0196  ·  Aditya Achar 24BCI0250",
      { placeholder: "names", bullet: false });
    s.addNotes("Since the last review we replaced the TF-IDF + VADER plan with a two-tier hybrid: a tiny model on a battery-powered device and a transformer on a nearby hub. Along the way we also ran a record attempt on the IMDb benchmark.");
  }

  // 2. Headline results
  {
    const s = content("Overview", "At a glance", "Three headline results",
      "All model choices were made on a 50,000-review validation set; the test set was scored once for the final ensemble.");
    await statCard(s, 0.6, 2.0, 3.85, 4.55, C.background2, "97.40%",
      "IMDb test accuracy, above the best published result (97.1%)",
      "With ~1M extra leak-free reviews (extra-data setting)", C.accent2, "FaTrophy");
    await statCard(s, 4.74, 2.0, 3.85, 4.55, C.accent4, "14–19×",
      "less device energy to match the transformer's accuracy",
      "ESP32-S3 datasheet currents; timings still to be measured", C.accent3, "FaBolt");
    await statCard(s, 8.88, 2.0, 3.85, 4.55, C.background2, "256\u00A0KB",
      "on-chip model reaching 92.3% test accuracy",
      "Fits an ESP32-S3 (512\u00A0KB RAM) with room to spare", C.accent2, "FaMicrochip");
    s.addNotes("Three results. First, our ensemble scores 97.40% on the IMDb test set, above the best published 97.1%, using extra training data. Second, the hybrid reaches the transformer's accuracy while using 14 to 19 times less device energy, based on datasheet currents. Third, a 256 KB model that fits on a $5 chip reaches 92.3%.");
  }

  // 3. What changed
  {
    const s = content("Overview", "Since the last review", "From one model to a two-tier hybrid");
    card(s, 0.6, 2.05, 5.3, 3.9, C.background2, "before");
    s.addText("Last review: the plan", T({ x: 0.9, y: 2.2, w: 4.7, h: 0.5, fontFace: "Cambria", fontSize: 20,
      bold: true, color: C.text2 }));
    s.addText([
      { text: "TF-IDF + VADER + logistic regression", options: { bullet: true, breakLine: true } },
      { text: "One model, CPU only", options: { bullet: true, breakLine: true } },
      { text: "25,000 IMDb training reviews", options: { bullet: true, breakLine: true } },
      { text: "Target: about 90% accuracy", options: { bullet: true } },
    ], T({ x: 0.9, y: 2.9, w: 4.75, h: 2.9, fontSize: 18, color: C.text1, paraSpaceAfter: 10, valign: "top" }));
    s.addImage({ data: await icon("FaArrowRight", "#9C7F89"), x: 6.17, y: 3.7, w: 0.6, h: 0.6 });
    card(s, 7.03, 2.05, 5.7, 3.9, C.accent4, "after");
    s.addText("Now: what we built", T({ x: 7.33, y: 2.2, w: 5.1, h: 0.5, fontFace: "Cambria", fontSize: 20,
      bold: true, color: C.accent3 }));
    s.addText([
      { text: "Tiny on-device model + transformer hub", options: { bullet: true, breakLine: true } },
      { text: "Learning to defer + energy-aware routing", options: { bullet: true, breakLine: true } },
      { text: "4.1M cleaned reviews, audited for test leakage", options: { bullet: true, breakLine: true } },
      { text: "Large transformers trained on cloud GPUs", options: { bullet: true, breakLine: true } },
      { text: "97.40% test accuracy", options: { bullet: true } },
    ], T({ x: 7.33, y: 2.9, w: 5.15, h: 2.9, fontSize: 18, color: C.text1, paraSpaceAfter: 10, valign: "top" }));
    s.addNotes("The VADER idea was a single extra feature on one CPU model. We replaced it with a system: a tiny model on the device, a transformer on a hub, and a router deciding which reviews are worth sending. That needed far more data and stronger models, which is where the rest of the work went.");
  }

  // 4. How the hybrid works
  pres.addSection({ title: "The system" });
  {
    const s = content("The system", "The system", "How the hybrid works",
      "Device: ESP32-S3 (~$5, 512 KB RAM). Hub: Raspberry Pi Zero 2 W ($15, 512 MB RAM). Same local network: no internet needed.");
    const y = 2.35, h = 1.45;
    const box = (x, w, fill, title, sub, titleColor = C.text2) => {
      card(s, x, y, w, h, fill, title);
      s.addText(title, T({ x: x + 0.2, y: y + 0.18, w: w - 0.4, h: 0.5, fontFace: "Cambria", fontSize: 18, bold: true,
        color: titleColor }));
      s.addText(sub, T({ x: x + 0.2, y: y + 0.7, w: w - 0.4, h: 0.65, fontSize: 14, color: C.text1, valign: "top" }));
    };
    const arrow = (x1, x2, yy) => s.addShape(pres.shapes.LINE, { x: x1, y: yy, w: x2 - x1, h: 0,
      line: { color: C.accent6, width: 2, endArrowType: "triangle" } });
    box(0.6, 2.2, C.background2, "Review", "Text typed, or speech converted to text");
    arrow(2.85, 3.3, y + h / 2);
    box(3.35, 3.0, C.accent4, "Tiny model", "On the device, 256 KB, answers in milliseconds", C.accent3);
    arrow(6.4, 6.85, y + h / 2);
    box(6.9, 2.55, C.accent5, "Worth sending?", "Router weighs expected gain against battery cost", C.accent2);
    arrow(9.5, 9.95, y + h / 2);
    box(10.0, 2.73, C.background2, "Transformer hub", "Answers the hard reviews, about 5–10% of them");
    s.addText("No: answer on the device", T({ x: 6.9, y: y + h + 0.25, w: 2.55, h: 0.4, fontSize: 14, bold: true,
      color: C.accent3, align: "center" }));
    s.addShape(pres.shapes.LINE, { x: 8.175, y: y + h, w: 0, h: 0.22, line: { color: C.accent6, width: 2,
      endArrowType: "triangle" } });
    s.addText("Yes", T({ x: 9.5, y: y + h / 2 - 0.42, w: 0.5, h: 0.35, fontSize: 14, bold: true, color: C.accent2, align: "center" }));
    card(s, 0.6, 5.15, 12.13, 1.45, C.background1, "router note");
    await iconCircle(s, 0.9, 5.42, 0.9, "FaRoute");
    s.addText([
      { text: "Two contributions in the router: ", options: { bold: true, color: C.text2 } },
      { text: "learning to defer (predict whether the hub would fix this review) and energy-aware routing (only send when the gain is worth the radio's battery cost).", options: { color: C.text1 } },
    ], T({ x: 2.05, y: 5.35, w: 10.4, h: 1.05, fontSize: 15, valign: "middle" }));
    s.addNotes("Every review hits the tiny model first. The router decides whether the expected accuracy gain from sending it to the hub is worth the battery the Wi-Fi radio costs. Most reviews never leave the device.");
  }

  // 5. Why energy: robots (content marked by the team for the slides)
  {
    const s = content("The system", "Why the energy angle", "Robots: a leading battery-powered use case",
      "Sources: Liu, Shi & Shin (2025); Pohland et al. (2026); Spezialetti, Placidi & Rossi (2020). All in papers/.");
    const rows = [
      ["FaBatteryQuarter", "Computing drains robot batteries, not just driving",
        "Measured robots use 30–90 W, and motors take only 16.6–54.6% of that. The rest is mostly computing and sensors."],
      ["FaMicrochip", "Big models on board cost hours of battery",
        "Larger onboard GPUs “drain robot batteries several hours faster.” Offloading helps but adds delay and network load."],
      ["FaRegSmile", "Robots care about sentiment",
        "Reading how a person feels, including frustration, is an established goal in human-robot interaction."],
    ];
    for (let i = 0; i < rows.length; i++) {
      const y = 1.95 + i * 1.32;
      await iconCircle(s, 0.6, y + 0.08, 0.85, rows[i][0], i === 1 ? C.accent2 : C.accent1);
      s.addText(rows[i][1], T({ x: 1.7, y, w: 6.9, h: 0.45, fontFace: "Cambria", fontSize: 19, bold: true, color: C.text2 }));
      s.addText(rows[i][2], T({ x: 1.7, y: y + 0.48, w: 6.9, h: 0.75, fontSize: 15, color: C.text1, valign: "top" }));
    }
    card(s, 9.0, 1.95, 3.73, 3.75, C.background2, "speech note");
    s.addText("Note", T({ x: 9.3, y: 2.2, w: 3.1, h: 0.4, fontSize: 14, bold: true, color: C.accent2, charSpacing: 1 }));
    s.addText("Robots hear speech, so a speech-to-text step runs first and the router works on the text. On a robot, the “device” tier is its own computer rather than an ESP32.",
      T({ x: 9.3, y: 2.7, w: 3.15, h: 2.8, fontFace: "Cambria", fontSize: 16, color: C.text2, valign: "top" }));
    s.addNotes("Robots are one of the biggest use cases, not the only one. The key numbers: motors are only 16.6 to 54.6% of measured robot power, and large onboard models cost hours of battery. Robots also care about sentiment: reading frustration is a long-standing human-robot-interaction goal.");
  }

  // 6. Use cases table (content marked by the team for the slides)
  {
    const s = content("The system", "Where it fits", "Use cases, ranked by fit",
      "T-Deck: ESP32-S3 handheld with keyboard and LoRa radio running Meshtastic off-grid messaging.");
    const head = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.accent1 } } });
    const rows = [
      ["Use case", "On battery?", "How text arrives", "Runs on ESP32?", "Fit"].map(head),
      ["Social, assistive, eldercare robots", "Yes, a major limit", "Speech → text", "No, robot's own computer", "Strongest story"],
      ["Off-grid messengers (LILYGO T-Deck)", "Yes", "Typed on its keyboard", "Yes, exact match", "Best hardware match"],
      ["Smartwatch, phone as hub", "Yes, tiny battery", "Voice replies", "Watch chip", "Believable"],
      ["Kids' smart toys", "Yes", "Speech", "Often", "Niche, privacy helps"],
      ["Battery or solar feedback kiosks", "Yes", "Typed feedback", "Yes", "Niche"],
      ["Drones, smart speakers", "Drones yes, speakers no", "No text, or plugged in", "—", "Not a fit"],
    ];
    s.addTable(rows, { x: 0.6, y: 1.95, w: 12.13, colW: [3.35, 2.25, 2.35, 2.35, 1.83], rowH: 0.62,
      fontFace: "Calibri", fontSize: 14, color: C.text1, valign: "middle", margin: [0, 0.12, 0, 0.12],
      border: { type: "solid", color: HEX.grid, pt: 0.75 }, fill: { color: C.background1 }, autoPage: false });
    s.addNotes("Ranked by fit. Robots tell the strongest story; off-grid messengers like the T-Deck are the closest hardware match, because people literally type messages into a battery-powered ESP32-S3.");
  }

  // 7. Data at scale
  pres.addSection({ title: "Data" });
  {
    const s = content("Data", "Data", "Millions of labelled reviews",
      "Labels: IMDb ≤4/10 negative, ≥7/10 positive; Amazon 1–2★ negative, 4–5★ positive. Middle ratings dropped; Amazon titles dropped (they state the rating).");
    const big = (x, fill, num, src, clean, note) => {
      card(s, x, 1.95, 5.9, 4.0, fill, src);
      s.addText(num, T({ x: x + 0.35, y: 2.2, w: 5.2, h: 1.0, fontFace: "Cambria", fontSize: 52, bold: true, color: C.accent2 }));
      s.addText(src, T({ x: x + 0.35, y: 3.25, w: 5.2, h: 0.8, fontSize: 17, bold: true, color: C.text2, valign: "top" }));
      s.addText(clean, T({ x: x + 0.35, y: 4.15, w: 5.2, h: 0.5, fontFace: "Cambria", fontSize: 22, bold: true, color: C.accent3 }));
      s.addText(note, T({ x: x + 0.35, y: 4.75, w: 5.2, h: 1.0, fontSize: 15, color: C.text1, valign: "top" }));
    };
    big(0.6, C.background2, "5,571,499", "IMDb Review Dataset (Kaggle, CC0)", "→ 4.1M clean reviews",
      "Same domain as the IMDb benchmark. The main extra training data.");
    big(6.83, C.accent4, "17.3M", "Amazon Reviews 2023, Movies & TV (Hugging Face)", "→ 12.0M clean reviews",
      "Short and mostly positive. Tested as extra data, but it did not help IMDb accuracy, so it was left out.");
    s.addNotes("Two large sources. The Kaggle scrape of IMDb is the same domain as the benchmark, 160 times more data than the official training set. Amazon's movie reviews were tested but didn't help, so the final models use the IMDb data.");
  }

  // 8. Leakage funnel
  {
    const s = content("Data", "Leakage audit", "91% of the test set was hiding in the download",
      "Round 1: exact and 200-character prefix/suffix matches. Round 2: test-set movies (163,409), test-review authors (635,853), near-duplicates (443).");
    s.addChart(pres.charts.BAR, [{ name: "Reviews", labels: ["Downloaded", "With a usable rating",
      "Copies of our splits and duplicates removed", "Movie- and author-disjoint from test"],
      values: [5571499, 4186661, 4099728, 3336925] }], {
      x: 0.5, y: 1.85, w: 7.9, h: 4.85, barDir: "bar", catAxisOrientation: "maxMin", chartColors: [HEX.mauve],
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", valAxisHidden: true,
      valAxisMinVal: 0, valAxisMaxVal: 6800000, showLegend: false, barGapWidthPct: 60, ...chartText,
      valGridLine: { style: "none" } });
    card(s, 8.75, 1.95, 3.98, 4.6, C.accent5, "leak callout");
    s.addText("23,636", T({ x: 9.05, y: 2.2, w: 3.4, h: 0.95, fontFace: "Cambria", fontSize: 46, bold: true, color: C.accent2 }));
    s.addText("copies of official test reviews were in the public scrape, and were removed", T({ x: 9.05, y: 3.15,
      w: 3.4, h: 1.1, fontSize: 16, bold: true, color: C.text2, valign: "top" }));
    s.addText("Training on them would have produced a fake, too-good score. Every later result uses data sharing no reviews, movies or authors with the test set.",
      T({ x: 9.05, y: 4.35, w: 3.4, h: 2.0, fontSize: 14, color: C.text1, valign: "top" }));
    s.addNotes("This is the most important hygiene result. 91% of the official test reviews were in the Kaggle download. We removed exact and near copies, then, after an adversarial review, every review of a test-set movie or by a test-review author. 3.34 million reviews remain.");
  }

  // 9. Honest evaluation
  {
    const s = content("Data", "Methodology", "How we kept the evaluation honest",
      "An adversarial reviewer agent audited the pipeline; it found misquoted records, a test-picked number and missed leaks, all fixed before the final run.");
    const steps = [
      ["Lock the test set", "The official 25,000 test reviews are never used for training or for any choice"],
      ["Clean the extra data", "Exact and near copies removed; no shared movies or authors with test"],
      ["Choose on val_pool", "50,000 reviews from held-out movies, length-matched to test"],
      ["Score test once", "The final ensemble is evaluated a single time"],
      ["Report uncertainty", "95% confidence interval, McNemar tests, de-duplicated test score"],
    ];
    const n = steps.length, colW = 12.13 / n;
    s.addShape(pres.shapes.LINE, { x: 0.6 + colW / 2, y: 2.62, w: colW * (n - 1), h: 0, line: { color: HEX.grid, width: 2 } });
    steps.forEach(([title, body], i) => {
      const x = 0.6 + i * colW;
      s.addShape(pres.shapes.OVAL, { x: x + colW / 2 - 0.36, y: 2.26, w: 0.72, h: 0.72,
        fill: { color: i === 3 ? C.accent2 : C.accent1 }, line: { type: "none" } });
      s.addText(String(i + 1), T({ x: x + colW / 2 - 0.36, y: 2.26, w: 0.72, h: 0.72, align: "center", valign: "middle",
        fontFace: "Cambria", fontSize: 20, bold: true, color: C.background1 }));
      card(s, x + 0.08, 3.3, colW - 0.16, 2.55, i % 2 ? C.accent4 : C.background2, `step ${i + 1}`);
      s.addText(title, T({ x: x + 0.28, y: 3.5, w: colW - 0.56, h: 0.75, fontFace: "Cambria", fontSize: 17, bold: true,
        color: C.text2, valign: "top" }));
      s.addText(body, T({ x: x + 0.28, y: 4.3, w: colW - 0.56, h: 1.4, fontSize: 14, color: C.text1, valign: "top" }));
    });
    s.addNotes("Five rules. The test set is locked. Extra data is cleaned so it shares nothing with test. Every choice is made on a separate 50,000-review validation set from held-out movies. The final ensemble is scored on test once. And we report uncertainty, not just a point estimate.");
  }

  // 10. On-device model
  pres.addSection({ title: "Models and results" });
  {
    const s = content("Models and results", "On-device model", "For the tiny model, more data beats more size",
      "Hashed word pairs, Naive Bayes weighting folded into the weights, int8 storage: no vocabulary on the device. Accuracy on the 5k validation split (first-round data).");
    s.addChart(pres.charts.BAR, [{ name: "Validation accuracy", labels: ["20k", "100k", "300k", "1M", "1.94M"],
      values: DATA.size_curve.map((p) => p[1]) }], {
      x: 0.5, y: 1.85, w: 7.4, h: 4.95, barDir: "col", chartColors: [HEX.mauve], showValue: true,
      dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', valAxisMinVal: 89, valAxisMaxVal: 93.5,
      valAxisMajorUnit: 1, valAxisLabelFormatCode: '0"%"', showLegend: false, barGapWidthPct: 55,
      showCatAxisTitle: true, catAxisTitle: "Training reviews (256 KB model)", catAxisTitleFontSize: 12,
      catAxisTitleColor: HEX.axis, ...chartText });
    card(s, 8.3, 1.95, 4.43, 4.6, C.background2, "size table");
    s.addText("Size on the chip (20k reviews)", T({ x: 8.6, y: 2.15, w: 3.9, h: 0.4, fontSize: 15, bold: true, color: C.text2 }));
    const sizes = DATA.size_kb.map(([kb, acc]) => [kb >= 1024 ? "1\u00A0MB" : `${kb}\u00A0KB`, `${(acc * 100).toFixed(1)}%`]);
    s.addTable(sizes.map(([a, b]) => [{ text: a, options: { bold: true, color: C.text2 } }, { text: b, options: { color: C.text1 } }]),
      { x: 8.6, y: 2.65, w: 3.8, colW: [1.9, 1.9], rowH: 0.42, fontFace: "Calibri", fontSize: 15,
        border: { type: "none" }, fill: { color: C.background2 }, margin: [0, 0, 0, 0], autoPage: false });
    s.addText([
      { text: "Cleaned data, final: ", options: { bold: true, color: C.accent2 } },
      { text: "256\u00A0KB → 92.32% test; 1\u00A0MB → 92.80% test.", options: { color: C.text1 } },
    ], T({ x: 8.6, y: 4.6, w: 3.85, h: 1.6, fontSize: 15, valign: "top" }));
    s.addNotes("Shrinking the table from 1 MB to 256 KB barely costs accuracy; adding data matters far more. With 1.94 million reviews the 256 KB model reached 92.76% on validation. Retrained on the fully cleaned data it scores 92.32% on test.");
  }

  // 11. Cascade
  {
    const s = content("Models and results", "Cascade", "Transformer accuracy from a fraction of the reviews",
      "First-round data: 256 KB chip model (92.69%) and DistilBERT hub (93.51%). Curves are on the test set with thresholds set by send rate (no labels used).");
    const labels = DATA.rates.map((r) => (r % 10 === 0 ? String(r) : ""));
    const hub = DATA.rates.map(() => DATA.hub);
    s.addChart(pres.charts.LINE, [
      { name: "Learned deferral", labels, values: DATA.learned },
      { name: "Confidence routing", labels, values: DATA.confidence },
      { name: "Perfect router (upper bound)", labels, values: DATA.oracle },
      { name: "Hub alone", labels, values: hub },
    ], { x: 0.5, y: 1.85, w: 7.9, h: 4.95, chartColors: [HEX.rose, HEX.sage, HEX.muted, HEX.pink],
      lineSize: 2, lineDataSymbol: "none", valAxisMinVal: 92, valAxisMaxVal: 97, valAxisMajorUnit: 1,
      valAxisLabelFormatCode: '0"%"', catAxisLabelFrequency: 1, catAxisLabelRotate: 0, showLegend: true, legendPos: "b", legendFontSize: 11,
      legendColor: HEX.ink, showCatAxisTitle: true, catAxisTitle: "Reviews sent to the hub (%)", catAxisTitleFontSize: 12,
      catAxisTitleColor: HEX.axis, ...chartText });
    const pts = [
      ["94.05%", "at 10.7% sent, threshold chosen on validation"],
      ["~5%", "of reviews sent is enough to match the hub"],
      ["±0.1 pt", "learned deferral vs confidence routing: no real gain yet"],
    ];
    pts.forEach(([big, txt], i) => {
      const y = 1.95 + i * 1.57;
      card(s, 8.75, y, 3.98, 1.4, i === 2 ? C.accent5 : (i ? C.accent4 : C.background2), big);
      s.addText(big, T({ x: 9.0, y: y + 0.15, w: 3.5, h: 0.6, fontFace: "Cambria", fontSize: 26, bold: true, color: C.accent2 }));
      s.addText(txt, T({ x: 9.0, y: y + 0.75, w: 3.5, h: 0.55, fontSize: 14, color: C.text1, valign: "top" }));
    });
    s.addNotes("Sending only about 5% of reviews matches the hub, and around 10% beats both models alone. Our learned-deferral router came out level with simple confidence routing, an honest negative result. A perfect router shows there is still room: 96.6% at about 4% sent.");
  }

  // 12. Energy
  {
    const s = content("Models and results", "Energy", "19× less device energy at the transformer's accuracy",
      "Energy per review = V × (CPU current × local time + share sent × (transmit current × send time + receive current × hub wait)).");
    s.addChart(pres.charts.BAR, [{ name: "mJ per review", labels: ["Send every review",
      "Cascade at hub accuracy (5% sent)", "Device only"], values: [DATA.energy.send_all,
      Math.round(DATA.energy.targets[2][1] * 10) / 10, DATA.energy.chip_only] }], {
      x: 0.5, y: 1.85, w: 7.9, h: 4.6, barDir: "bar", catAxisOrientation: "maxMin",
      chartColors: [HEX.muted, HEX.rose, HEX.sage], showValue: true, dataLabelPosition: "outEnd",
      dataLabelFormatCode: '0.0" mJ"', valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 360, showLegend: false,
      barGapWidthPct: 55, ...chartText, valGridLine: { style: "none" } });
    card(s, 8.75, 1.95, 3.98, 4.6, C.background2, "assumptions");
    s.addText("Assumptions", T({ x: 9.05, y: 2.15, w: 3.4, h: 0.4, fontSize: 15, bold: true, color: C.accent2 }));
    s.addText([
      { text: "From the ESP32-S3 datasheet: ", options: { bold: true, breakLine: true } },
      { text: "Wi-Fi transmit 283 mA, receive 88 mA, CPU 51.2 mA, at 3.3 V", options: { breakLine: true } },
      { text: " ", options: { breakLine: true } },
      { text: "Placeholders, to be measured: ", options: { bold: true, breakLine: true } },
      { text: "5 ms on the chip, 10 ms to send, 1 s waiting for the hub", options: { breakLine: true } },
      { text: " ", options: { breakLine: true } },
      { text: "The 14–19× saving holds for hub waits from 0.1 to 2 s.", options: { italic: true } },
    ], T({ x: 9.05, y: 2.65, w: 3.45, h: 3.7, fontSize: 14, color: C.text1, valign: "top" }));
    s.addNotes("The radio dominates. Sending every review costs about 300 millijoules each with a one-second hub wait; matching the hub's accuracy through the cascade costs about 16. The currents come from the datasheet; the timings are placeholders until we measure them on the board.");
  }

  // 13. Record attempt
  {
    const s = content("Models and results", "Record attempt", "97.40%: above the best published IMDb result",
      "Published: ERNIE-Doc (ACL 2021), XLNet (NeurIPS 2019), LlamBERT (2024, extra data). Ours: chosen on val_pool; ensemble = ELECTRA + DeBERTa + 1 MB n-gram, stacked.");
    const rows = [
      ["LlamBERT (published)", 96.68, HEX.muted], ["XLNet (published)", 96.80, HEX.muted],
      ["ERNIE-Doc (published best)", 97.10, HEX.muted], ["RoBERTa-large, official data only", 96.54, HEX.mauve],
      ["RoBERTa-large + 1M reviews", 97.21, HEX.mauve], ["ELECTRA-large + 1M reviews", 97.22, HEX.mauve],
      ["DeBERTa-v3-large + 1M reviews", 97.33, HEX.mauve], ["Our ensemble", 97.40, HEX.rose],
    ];
    s.addChart(pres.charts.BAR, [{ name: "Test accuracy", labels: rows.map((r) => r[0]), values: rows.map((r) => r[1]) }], {
      x: 0.5, y: 1.85, w: 8.2, h: 4.95, barDir: "bar", catAxisOrientation: "maxMin", chartColors: rows.map((r) => r[2]),
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"%"', valAxisMinVal: 96.0,
      valAxisMaxVal: 97.7, valAxisHidden: true, showLegend: false, barGapWidthPct: 45, ...chartText,
      valGridLine: { style: "none" } });
    card(s, 9.0, 1.95, 3.73, 4.6, C.background2, "record callout");
    s.addText("97.40%", T({ x: 9.3, y: 2.2, w: 3.2, h: 0.95, fontFace: "Cambria", fontSize: 46, bold: true, color: C.accent2 }));
    s.addText("IMDb test accuracy", T({ x: 9.3, y: 3.15, w: 3.2, h: 0.45, fontSize: 16, bold: true, color: C.text2 }));
    s.addText([
      { text: "95% CI 97.21–97.58%", options: { bullet: true, breakLine: true } },
      { text: "De-duplicated test: 97.40%", options: { bullet: true, breakLine: true } },
      { text: "Beats our best single model (p\u00A0=\u00A00.046)", options: { bullet: true } },
    ], T({ x: 9.3, y: 3.75, w: 3.25, h: 2.5, fontSize: 14, color: C.text1, paraSpaceAfter: 8, valign: "top" }));
    s.addNotes("Our reproduction of RoBERTa-large on the official data scores exactly the published 96.54%, so the setup is sound. Adding a million leak-free reviews lifts every model above 97.2%, and the ensemble reaches 97.40%. Even the low end of its 95% interval is above ERNIE-Doc's 97.1%.");
  }

  // 14. How the record was built
  {
    const s = content("Models and results", "Implementation", "How the record was built",
      "Cloud compute: Modal H100 80 GB GPUs, about 400 reviews per second for RoBERTa-large (about 100× the laptop). Total cost $17.99 of $30 in free credits.");
    const cols = [
      ["FaDatabase", "Data", ["Official 20k training reviews + 1M cleaned pool reviews", "Tokens cached on cheap CPU machines", "Long reviews cut to first 128 + last 382 tokens"]],
      ["FaServer", "Training", ["RoBERTa-large, ELECTRA-large, DeBERTa-v3-large", "One epoch, bf16, AdamW, batch\u00A032", "Checkpoints and hard time limits on every run"]],
      ["FaLayerGroup", "Combining", ["Long reviews re-read in sliding windows (kept only where it helped on validation)", "Stacking chosen by 5-fold cross-validation on val_pool", "Test scored once"]],
    ];
    for (let i = 0; i < cols.length; i++) {
      const x = 0.6 + i * 4.13;
      card(s, x, 1.95, 3.87, 4.6, i === 1 ? C.accent4 : C.background2, cols[i][1]);
      await iconCircle(s, x + 0.3, 2.2, 0.75, cols[i][0], i === 1 ? C.accent3 : C.accent1);
      s.addText(cols[i][1], T({ x: x + 1.2, y: 2.32, w: 2.4, h: 0.5, fontFace: "Cambria", fontSize: 20, bold: true, color: C.text2 }));
      s.addText(cols[i][2].map((t, j, a) => ({ text: t, options: { bullet: true, breakLine: j < a.length - 1 } })),
        T({ x: x + 0.3, y: 3.2, w: 3.3, h: 3.2, fontSize: 15, color: C.text1, paraSpaceAfter: 10, valign: "top" }));
    }
    s.addNotes("Three large transformers, each trained once on the official training set plus a million cleaned reviews, on rented H100 GPUs. Every combination choice was made on the 50,000-review validation set, and the test set was scored once at the end.");
  }

  // 15. Claims and caveats
  {
    const s = content("Models and results", "Honest reporting", "What we can claim, and what we can't");
    const col = async (x, fill, iconName, iconFill, head, items) => {
      card(s, x, 1.95, 5.95, 4.6, fill, head);
      await iconCircle(s, x + 0.3, 2.18, 0.7, iconName, iconFill);
      s.addText(head, T({ x: x + 1.2, y: 2.3, w: 4.5, h: 0.5, fontFace: "Cambria", fontSize: 20, bold: true, color: C.text2 }));
      s.addText(items.map((t, j, a) => ({ text: t, options: { bullet: true, breakLine: j < a.length - 1 } })),
        T({ x: x + 0.3, y: 3.1, w: 5.35, h: 3.3, fontSize: 15, color: C.text1, paraSpaceAfter: 10, valign: "top" }));
    };
    await col(0.6, C.accent4, "FaCheck", C.accent3, "We can claim", [
      "97.40% on IMDb test, using ~1M extra rating-labelled IMDb reviews, de-duplicated and movie- and author-disjoint from test",
      "Significantly better than our best single model (p = 0.046) and the official-data baseline (p ≈ 6 × 10⁻²²)",
      "Its 95% confidence interval (97.21–97.58%) sits above ERNIE-Doc's 97.1%",
    ]);
    await col(6.78, C.background2, "FaExclamation", C.accent2, "Caveats", [
      "An extra-training-data result, not an official-data-only one",
      "One training run per model: no repeated seeds yet",
      "About 2.9% of IMDb test labels are wrong, so ~97% is the practical ceiling",
      "Energy figures use placeholder timings until measured on hardware",
    ]);
    s.addNotes("How we state the result matters. It belongs in the extra-training-data category, it comes from single runs, and the IMDb test labels themselves cap realistic accuracy near 97%. The energy numbers still need real hardware measurements.");
  }

  // 16. Tech stack and lessons
  {
    const s = content("Models and results", "Implementation", "Tech stack and engineering lessons",
      "All code, data steps and 49 cited papers (with BibTeX) are in the project folder; a live dashboard tracks background jobs.");
    const tiles = [
      ["FaPython", "Python\u00A03.12, PyTorch\u00A02.14", "Apple GPU (MPS) locally, CUDA in the cloud"],
      ["FaRobot", "Hugging Face transformers\u00A05.20", "RoBERTa, ELECTRA, DeBERTa, DistilBERT"],
      ["FaChartBar", "scikit-learn\u00A01.9", "Hashed n-grams, logistic regression, stacking"],
      ["FaCloud", "Modal H100 GPUs", "Cost-capped, checkpointed cloud training"],
      ["FaStream", "pyarrow, ijson", "Streaming 23M reviews within 18 GB of RAM"],
      ["FaDownload", "Kaggle and Hugging Face", "IMDb scrape and Amazon Reviews 2023"],
    ];
    for (let i = 0; i < tiles.length; i++) {
      const x = 0.6 + (i % 3) * 2.75, y = 1.95 + Math.floor(i / 3) * 2.35;
      card(s, x, y, 2.55, 2.15, i % 2 ? C.accent4 : C.background2, tiles[i][1]);
      await iconCircle(s, x + 0.25, y + 0.22, 0.6, tiles[i][0], C.accent1);
      s.addText(tiles[i][1], T({ x: x + 0.25, y: y + 0.95, w: 2.1, h: 0.55, fontSize: 15, bold: true, color: C.text2, valign: "top" }));
      s.addText(tiles[i][2], T({ x: x + 0.25, y: y + 1.45, w: 2.1, h: 0.6, fontSize: 12, color: C.text1, valign: "top" }));
    }
    card(s, 9.0, 1.95, 3.73, 4.5, C.accent5, "lessons");
    s.addText("Lessons learned", T({ x: 9.3, y: 2.15, w: 3.2, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.accent2 }));
    s.addText([
      { text: "DeBERTa loaded in float16 and turned every weight into NaN: force float32", options: { bullet: true, breakLine: true } },
      { text: "Apple GPUs recompile for each input length: pad to multiples of 64", options: { bullet: true, breakLine: true } },
      { text: "Public scrapes contain the benchmark: always de-duplicate", options: { bullet: true } },
    ], T({ x: 9.3, y: 2.75, w: 3.2, h: 3.55, fontSize: 14, color: C.text2, paraSpaceAfter: 10, valign: "top" }));
    s.addNotes("The stack is standard open-source Python. Three lessons cost us the most time: a float16 checkpoint silently breaking training, Apple GPU recompilation, and benchmark leakage in public data.");
  }

  // 17. Next steps
  pres.addSection({ title: "Next steps" });
  {
    const s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Next steps" });
    s.addText("NEXT STEPS", { placeholder: "eyebrow", charSpacing: 2, bullet: false });
    s.addText("What happens next", { placeholder: "title" });
    const items = [
      ["FaBolt", "Measure real energy on an ESP32-S3, a Raspberry Pi Zero 2 W and an INA219 current sensor"],
      ["FaRedo", "Rerun the cascade and router on the cleaned data, with a stronger hub"],
      ["FaFlask", "Repeat training with more seeds, and test on corrected IMDb labels"],
      ["FaPenNib", "Write up the paper and final review materials"],
    ];
    for (let i = 0; i < items.length; i++) {
      const y = 2.2 + i * 1.0;
      await iconCircle(s, 0.6, y, 0.62, items[i][0], C.accent2);
      s.addText(items[i][1], T({ x: 1.45, y: y - 0.02, w: 10.8, h: 0.66, fontSize: 18, color: C.background1, valign: "middle" }));
    }
    s.addText("Feedback on the energy framing and the record claim is welcome before the final write-up.",
      T({ x: 0.6, y: 6.35, w: 11.5, h: 0.5, fontFace: "Cambria", italic: true, fontSize: 16, color: C.background2 }));
    s.addNotes("Next: real energy measurements on hardware, rerunning the cascade on the cleaned data, repeated seeds and corrected labels for the record result, and the write-up.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}

build().catch((e) => { console.error(e); process.exit(1); });
