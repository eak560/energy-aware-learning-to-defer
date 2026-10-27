// Builds slides/paper_presentation.pptx: the talk for the IEEE paper (paper/energy_aware_routing_ieee.docx).
// Palette and fonts continue the project decks (mauve, sage, blush; Cambria + Calibri).
// Numbers are read from outputs/defer_results_*.json and paper/energy_table.json.
//   PPTX_SKILL_DIR=<pptx skill dir> ICON_DEPS_DIR=<dir with react-icons, react, react-dom, sharp> \
//     node slides/build_paper_deck.js
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

const ROOT = path.join(__dirname, "..");
const readJson = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const DEFER = {
  weak: readJson("outputs/defer_results_v1_distilbert20k.json"),
  distil: readJson("outputs/defer_results_distilbert_1m.json"),
  roberta: readJson("outputs/defer_results_roberta_base_1m.json"),
};
const ENERGY = readJson("paper/energy_table.json");
const OUT = path.join(__dirname, "paper_presentation.pptx");

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
  sage: "4A5A50", muted: "B9AEB1", pink: "F3A9B7", mint: "D9E3DC", blush: "F7EFF1" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Energy-Aware Routing of Sentiment Analysis Between a Microcontroller and a Transformer Hub";
pres.author = "Ehsan Abdulkhader, Danyson Antony, Aditya Achar";
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
// Slide-number badge: a sage circle image (slide layouts cannot hold ellipse shapes).
const CIRCLE = "image/png;base64," + require("child_process").execFileSync(process.execPath, ["-e",
  `const sharp=require(${JSON.stringify(require.resolve("sharp", { paths: [DEPS] }))});` +
  `sharp(Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><circle cx="64" cy="64" r="64" fill="#D9E3DC"/></svg>')).png().toBuffer().then(b=>process.stdout.write(b.toString("base64")))`]).toString();
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.2, w: 12.1, h: 2.5, fontSize: 36,
      bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.6, y: 3.9, w: 11.6, h: 0.6, fontSize: 20,
      italic: true, color: C.background2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "names", type: "body", x: 0.6, y: 5.3, w: 12.1, h: 0.45, fontSize: 16,
      bold: true, color: C.background1, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "affil", type: "body", x: 0.6, y: 5.8, w: 12.1, h: 0.4, fontSize: 14,
      color: C.background2, margin: 0 }, text: "" } },
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
    { placeholder: { options: { name: "footer", type: "body", x: 0.6, y: 6.95, w: 11.5, h: 0.34, fontSize: 11,
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
const chartText = () => ({ catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  legendFontFace: "+mn-lt", catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
  catAxisLabelColor: HEX.ink, valAxisLabelColor: HEX.axis, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  catAxisTitleColor: HEX.axis, valAxisTitleColor: HEX.axis, catAxisTitleFontSize: 12, valAxisTitleFontSize: 12,
  dataLabelFontSize: 12, dataLabelColor: HEX.ink, legendFontSize: 12, legendColor: HEX.ink,
  valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" } });
const pct = (v, d = 2) => (v * 100).toFixed(d);

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

async function statCard(s, x, y, w, h, big, label, small, bigColor = C.accent2, iconName = null) {
  card(s, x, y, w, h, C.background2, `stat ${big}`);
  if (iconName) await iconCircle(s, x + 0.3, y + 0.3, 0.7, iconName, bigColor);
  const top = iconName ? y + 1.1 : y + 0.3;
  s.addText(big, T({ x: x + 0.3, y: top, w: w - 0.6, h: 0.9, fontFace: "Cambria", fontSize: 40, bold: true,
    color: bigColor, valign: "middle" }));
  s.addText(label, T({ x: x + 0.3, y: top + 0.95, w: w - 0.6, h: 0.75, fontSize: 16, bold: true, color: C.text2,
    valign: "top" }));
  if (small) s.addText(small, T({ x: x + 0.3, y: y + h - 0.75, w: w - 0.6, h: 0.55, fontSize: 12, color: C.accent6,
    valign: "bottom" }));
}

function bulletList(items, opts) {
  return [items.map((t, i) => ({ text: t, options: { bullet: { indent: 18 }, breakLine: i < items.length - 1 } })),
    T({ fontSize: 16, color: C.text1, paraSpaceAfter: 8, valign: "top", ...opts })];
}

// ------------------------------------------------------------------ talk structure: four presenters
const P = { ehsan: "Ehsan Abdulkhader", danyson: "Danyson Antony", aditya: "Aditya Achar" };
const PARTS = [
  { who: P.aditya, part: "Part 1", topic: "The problem, the idea and the data", slides: "Slides 1–8", icon: "FaLightbulb" },
  { who: P.danyson, part: "Part 2", topic: "Models, cost and learned deferral", slides: "Slides 9–15", icon: "FaBrain" },
  { who: P.ehsan, part: "Part 3", topic: "Results, energy and conclusions", slides: "Slides 16–22", icon: "FaBolt" },
];
const SCRIPT = []; // every slide's spoken script, also written to presenter_scripts.md

// Speaker notes carry the presenter, a time budget and the word-for-word script.
function say(s, who, seconds, title, text) {
  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  s.addNotes(`${who} · about ${time} min\n\n${text}`);
  SCRIPT.push({ who, seconds, title, text });
}

function talk(section, topic, who, title, footer) {
  return content(section, `${topic}  ·  ${who}`, title, footer);
}

const COSTS = [ // Modal billing report, itemised per run (USD)
  ["DeBERTa-v3-large, 1M", 9.03], ["RoBERTa-large, 1M", 3.71], ["ELECTRA-large, 1M", 3.68],
  ["RoBERTa-base hub, 1M", 1.64], ["DistilBERT hub, 1M", 0.91], ["Long-review predictions", 0.63],
  ["RoBERTa-large, 20k", 0.43], ["Tokenising, upload, other", 0.27],
];
const BATTERY_J = 2.0 * 3.7 * 3600; // illustrative 2,000 mAh, 3.7 V cell
const CHIP = readJson("outputs/chip_model_results.json");

// ------------------------------------------------------------------ slides
async function build() {
  // 1. Title
  pres.addSection({ title: "Part 1: Problem, idea and data" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Part 1: Problem, idea and data" });
  s.addText([{ text: "Energy-Aware Routing of Sentiment Analysis", options: { breakLine: true } },
    { text: "Between a Microcontroller and a Transformer Hub" }], { placeholder: "title" });
  s.addText("Does learning to defer beat confidence routing on a battery-powered device?", { placeholder: "subtitle" });
  s.addText("Ehsan Abdulkhader 24BCT0089  ·  Danyson Antony 24BAI0196  ·  Aditya Achar 24BCI0250", { placeholder: "names" });
  s.addText("School of Computer Science and Engineering, Vellore Institute of Technology, Vellore",
    { placeholder: "affil" });
  say(s, P.aditya, 30, "Title",
    "Good morning, everyone. I'm Aditya Achar, and with me are Danyson Antony and Ehsan Abdulkhader, " +
    "from the School of Computer Science and Engineering at VIT. Our paper asks a simple question with a battery " +
    "attached to it: when a tiny device reads a piece of text and isn't sure what it means, when should it ask a " +
    "bigger model for help? Every request costs radio energy, so which requests are actually worth sending?");

  // 2. Agenda
  s = talk("Part 1: Problem, idea and data", "Agenda", P.aditya, "Three parts, three presenters, about 25 minutes");
  for (let i = 0; i < PARTS.length; i++) {
    const x = 0.6 + i * 4.1, p = PARTS[i];
    card(s, x, 1.95, 3.8, 4.4, C.background2, p.part);
    await iconCircle(s, x + 0.3, 2.25, 0.75, p.icon, i % 2 ? C.accent3 : C.accent2);
    s.addText(p.part.toUpperCase(), T({ x: x + 0.3, y: 3.25, w: 3.2, h: 0.3, fontSize: 12, bold: true,
      color: C.accent6, charSpacing: 2 }));
    s.addText(p.topic, T({ x: x + 0.3, y: 3.6, w: 3.2, h: 0.8, fontFace: "Cambria", fontSize: 20, bold: true,
      color: C.text2, valign: "top" }));
    s.addText(p.who, T({ x: x + 0.3, y: 4.6, w: 3.2, h: 0.4, fontSize: 16, bold: true, color: i % 2 ? C.accent3 : C.accent2 }));
    s.addText(p.slides, T({ x: x + 0.3, y: 5.05, w: 3.2, h: 0.35, fontSize: 14, color: C.accent6 }));
  }
  say(s, P.aditya, 30, "Agenda",
    "We've split the talk into three parts. I'll set up the problem, the system and the question we asked, and " +
    "explain the data and how we kept it free of test-set leakage. Danyson will cover how we trained the models, " +
    "what that cost, and the learned deferral method with its main result. Ehsan will show the results across all " +
    "hubs, the energy analysis, what it means for battery life, our limitations and the takeaways. We'll take " +
    "questions at the end.");

  // 3. Motivation
  s = talk("Part 1: Problem, idea and data", "Motivation", P.aditya,
    "Battery devices need to understand text, but transformers don't fit on them",
    "Robot power: Liu et al. 2025; ESP32-S3 datasheet v2.2; DistilBERT: Sanh et al. 2019");
  const uses = [
    ["FaRobot", "Social and assistive robots", "Computing is a major battery drain: motors are only 16.6–54.6% of a robot's power"],
    ["FaKeyboard", "Off-grid messengers", "People type straight into an ESP32-S3, e.g. Meshtastic on a LILYGO T-Deck"],
    ["FaClock", "Wearables", "A smartwatch that leans on the phone in your pocket as its hub"],
  ];
  for (let i = 0; i < uses.length; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.95, 3.8, 2.65, C.background2, uses[i][1]);
    await iconCircle(s, x + 0.3, 2.25, 0.75, uses[i][0], C.accent3);
    s.addText(uses[i][1], T({ x: x + 0.3, y: 3.15, w: 3.2, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
    s.addText(uses[i][2], T({ x: x + 0.3, y: 3.62, w: 3.2, h: 0.9, fontSize: 14, color: C.text1, valign: "top" }));
  }
  s.addText([
    { text: "512 KB", options: { fontFace: "Cambria", fontSize: 36, bold: true, color: C.accent2, breakLine: true } },
    { text: "of on-chip SRAM on an ESP32-S3", options: { fontSize: 15, color: C.text1 } },
  ], T({ x: 0.9, y: 5.0, w: 4.6, h: 1.3, valign: "middle" }));
  s.addText("vs", T({ x: 5.6, y: 5.0, w: 1.0, h: 1.3, fontFace: "Cambria", fontSize: 26, italic: true,
    color: C.accent6, align: "center", valign: "middle" }));
  s.addText([
    { text: "66 million", options: { fontFace: "Cambria", fontSize: 36, bold: true, color: C.accent2, breakLine: true } },
    { text: "parameters in DistilBERT, the smallest common transformer", options: { fontSize: 15, color: C.text1 } },
  ], T({ x: 6.8, y: 5.0, w: 5.6, h: 1.3, valign: "middle" }));
  say(s, P.aditya, 75, "Motivation",
    "Start with who needs this. Social and assistive robots react to what people say, and on mobile robots " +
    "computing is a major battery drain: measured studies find the motors are only about 17 to 55 percent of total " +
    "power. Off-grid messengers, like a Meshtastic T-Deck, have people typing straight into an ESP32-S3 " +
    "microcontroller. And wearables lean on the phone in your pocket. All of these handle text, and all of them run " +
    "on batteries. The problem is size. An ESP32-S3 has 512 kilobytes of on-chip memory. DistilBERT, one of the " +
    "smallest common transformers, has 66 million parameters. It simply does not fit. A tiny model does fit, but " +
    "it is several points less accurate. So the device needs help from somewhere.");

  // 4. Related work
  s = talk("Part 1: Problem, idea and data", "Related work", P.aditya, "Three lines of work meet here, and one gap is untested",
    "Full references in the paper (IEEE format, 36 sources)");
  const fields = [
    ["FaLayerGroup", C.accent2, "Cascades", ["Viola–Jones detector, 2001", "BranchyNet early exits, 2017",
      "Confidence cascades for NLP: Varshney & Baral, 2022", "Edge-cloud cascades: Huang et al., 2025"]],
    ["FaUserCheck", C.accent3, "Learning to defer", ["Selective classification: Geifman & El-Yaniv, 2017",
      "Calibration: Guo et al., 2017", "Learning to defer: Madras et al., 2018", "Consistent losses: Mozannar & Sontag, 2020"]],
    ["FaBatteryHalf", C.accent1, "TinyML and energy", ["EdgeBERT on custom accelerators, 2021",
      "Energy-aware multi-exit TinyML, 2026", "Small transformers lose accuracy: Turc et al., 2019",
      "NLP's energy cost: Strubell et al., 2019"]],
  ];
  for (let i = 0; i < fields.length; i++) {
    const x = 0.6 + i * 4.1, [ic, col, name, refs] = fields[i];
    card(s, x, 1.95, 3.8, 3.3, C.background2, name);
    await iconCircle(s, x + 0.3, 2.2, 0.65, ic, col);
    s.addText(name, T({ x: x + 1.1, y: 2.3, w: 2.5, h: 0.45, fontSize: 19, bold: true, color: col }));
    s.addText(...bulletList(refs, { x: x + 0.35, y: 3.05, w: 3.25, h: 2.1, fontSize: 14, paraSpaceAfter: 5 }));
  }
  card(s, 0.6, 5.5, 12.1, 1.1, C.accent4, "gap");
  s.addText([
    { text: "The gap: ", options: { bold: true, color: C.accent3 } },
    { text: "learned deferral has not been tested from a microcontroller, where the deferral model itself must fit " +
      "in 128 KB and the cost that matters is battery energy.", options: { color: C.text1 } },
  ], T({ x: 0.9, y: 5.5, w: 11.5, h: 1.1, fontSize: 16, valign: "middle" }));
  say(s, P.aditya, 75, "Related work",
    "Our work sits where three lines of research meet. First, cascades: run a cheap model first and an expensive " +
    "one only when needed. That goes back to the Viola–Jones face detector, and in language processing to " +
    "confidence-based cascades by Varshney and Baral. Second, selective classification and learning to defer: " +
    "instead of only knowing 'I might be wrong', a model learns when an expert would actually do better, as in " +
    "Madras and colleagues, and Mozannar and Sontag. Third, TinyML and energy, where systems like EdgeBERT optimise " +
    "transformer inference on custom chips. What nobody had tested is learned deferral on a microcontroller, where " +
    "the deferral model itself must fit in 128 kilobytes and the cost that matters is battery energy. That is the " +
    "gap we target.");

  // 5. System
  s = talk("Part 1: Problem, idea and data", "The system", P.aditya,
    "A tiny model on the device, a transformer on the hub, and a rule for when to ask");
  card(s, 0.6, 1.95, 5.3, 3.55, C.background2, "device card");
  await iconCircle(s, 0.9, 2.2, 0.7, "FaMicrochip", C.accent2);
  s.addText("Device: ESP32-S3, on battery", T({ x: 1.75, y: 2.3, w: 4.0, h: 0.5, fontSize: 19, bold: true, color: C.text2 }));
  s.addText(...bulletList([
    "Hash word 1–2-grams (no vocabulary stored)",
    "Chip model, 256 KB int8: p(x), 92.7% accurate",
    "Deferral model, 128 KB: g(x)",
    "Answer locally for about 0.8 mJ",
  ], { x: 0.95, y: 3.15, w: 4.75, h: 2.2 }));
  card(s, 7.4, 1.95, 5.3, 3.55, C.background2, "hub card");
  await iconCircle(s, 7.7, 2.2, 0.7, "FaServer", C.accent3);
  s.addText("Hub: Raspberry Pi Zero 2 W", T({ x: 8.55, y: 2.3, w: 4.0, h: 0.5, fontSize: 19, bold: true, color: C.text2 }));
  s.addText(...bulletList([
    "512 MB of RAM, about USD 15",
    "Int8 transformer: DistilBERT or RoBERTa-base",
    "95.8–96.7% accurate",
    "Sends the label back",
  ], { x: 7.75, y: 3.15, w: 4.75, h: 2.2 }));
  s.addShape(pres.shapes.LINE, { x: 6.05, y: 3.25, w: 1.2, h: 0, line: { color: HEX.ink, width: 2, endArrowType: "triangle" } });
  s.addShape(pres.shapes.LINE, { x: 6.05, y: 4.15, w: 1.2, h: 0, line: { color: HEX.ink, width: 2, beginArrowType: "triangle" } });
  s.addText("review (Wi-Fi)", T({ x: 5.95, y: 2.8, w: 1.4, h: 0.35, fontSize: 12, color: C.accent6, align: "center" }));
  s.addText("label", T({ x: 5.95, y: 4.25, w: 1.4, h: 0.35, fontSize: 12, color: C.accent6, align: "center" }));
  card(s, 0.6, 5.8, 12.1, 0.95, C.accent4, "decision rule");
  s.addText([
    { text: "Send only if  g(x) > λ", options: { fontFace: "Cambria", fontSize: 22, bold: true, color: C.accent3 } },
    { text: "     λ = what one Wi-Fi send costs, in accuracy; sweeping it traces accuracy vs. battery",
      options: { fontSize: 15, color: C.text1 } },
  ], T({ x: 0.9, y: 5.8, w: 11.6, h: 0.95, valign: "middle" }));
  say(s, P.aditya, 75, "The system",
    "Here is the system. On the left is the device: an ESP32-S3 on battery. It hashes the review's words and word " +
    "pairs, with no vocabulary stored, and looks up a 256-kilobyte table of 8-bit weights. That gives p of x, its " +
    "probability that the review is positive, and on its own it is 92.7 percent accurate. A second, 128-kilobyte " +
    "model gives g of x: how much sending this review would help. Together the two models use 384 of the chip's " +
    "512 kilobytes. On the right is the hub: a Raspberry Pi Zero 2 W, " +
    "about 15 dollars with 512 megabytes of RAM, running an 8-bit transformer that is 95.8 to 96.7 percent accurate. " +
    "The rule is at the bottom: send only if g of x is greater than lambda. Lambda is the price of one Wi-Fi send, " +
    "measured in accuracy. Raise it and the device sends less; lower it and it sends more. Sweeping lambda traces " +
    "accuracy against battery.");

  // 6. Two routers
  s = talk("Part 1: Problem, idea and data", "The question", P.aditya, "Which reviews should the device send to the hub?");
  const routers = [
    ["FaBalanceScale", C.accent2, "Confidence routing", "Send the reviews the device is least sure about",
      ["Score: 1 − max(p, 1 − p)", "Knows “I might be wrong”", "Free: no extra model"]],
    ["FaBrain", C.accent3, "Learned deferral", "Predict whether the hub would fix the device's answer",
      ["Gain = hub right − device right (−1, 0, +1)", "g(x) = P(fix) − P(break), 128 KB model",
        "Trained on 300k held-out reviews"]],
  ];
  for (let i = 0; i < 2; i++) {
    const x = 0.6 + i * 6.2, [ic, col, name, idea, pts] = routers[i];
    card(s, x, 1.95, 5.9, 3.65, C.background2, name);
    await iconCircle(s, x + 0.35, 2.25, 0.75, ic, col);
    s.addText(name, T({ x: x + 1.3, y: 2.3, w: 4.3, h: 0.5, fontSize: 21, bold: true, color: col }));
    s.addText(idea, T({ x: x + 1.3, y: 2.8, w: 4.3, h: 0.6, fontSize: 15, italic: true, color: C.text1 }));
    s.addText(...bulletList(pts, { x: x + 0.4, y: 3.75, w: 5.2, h: 1.7 }));
  }
  s.addText([
    { text: "Hypothesis: ", options: { bold: true, color: C.accent2 } },
    { text: "learned deferral should skip reviews the hub would also get wrong, or that the device already gets " +
      "right, so it reaches the same accuracy with fewer sends.", options: { color: C.text1 } },
  ], T({ x: 0.6, y: 5.95, w: 12.1, h: 0.8, fontSize: 16, valign: "middle" }));
  say(s, P.aditya, 60, "The question",
    "So the real question is how to compute g. The standard answer is confidence routing: send the reviews the " +
    "device is least sure about, scored as one minus its confidence. It is free; there is no extra model. The " +
    "alternative is learned deferral: train a second small model to predict whether the hub would actually fix " +
    "the device's answer. Its training label is the gain: plus one if the hub fixes the answer, minus one if the " +
    "hub breaks a correct answer, and zero otherwise. Our hypothesis was that learned deferral would skip reviews " +
    "the hub would also get wrong, or that the device already gets right, and so reach the same accuracy with " +
    "fewer sends. To test that fairly we needed clean data, so let me show you how we built it.");

  // 7. Data sources
  s = talk("Part 1: Problem, idea and data", "Data and labels", P.aditya,
    "22.8 million scraped reviews, cleaned and split",
    "Official IMDb splits from Maas et al. 2011; Kaggle IMDb review dataset (Biswas); Amazon Reviews 2023, Movies & TV");
  const flow = [
    ["FaDownload", C.accent2, "1. Sources", ["Official IMDb: 50,000 reviews", "Scraped IMDb (Kaggle): 5.5M",
      "Amazon Movies & TV: 17.3M"]],
    ["FaTags", C.accent1, "2. Label and clean", ["IMDb: ≤ 4/10 negative, ≥ 7/10 positive", "Amazon: 1–2★ vs 4–5★",
      "Middle ratings dropped; duplicates removed", "Left: 4.1M IMDb, 12.0M Amazon"]],
    ["FaColumns", C.accent3, "3. Split", ["Test: official 25,000 (never changed)", "Train 20,000 / validation 5,000",
      "Pool training slice: 1,532,574", "Deferral slice: 300,000 (held out)", "val_pool: 50,000 unseen movies"]],
  ];
  for (let i = 0; i < flow.length; i++) {
    const x = 0.6 + i * 4.2, [ic, col, name, pts] = flow[i];
    card(s, x, 1.95, 3.7, 4.65, C.background2, name);
    await iconCircle(s, x + 0.3, 2.2, 0.65, ic, col);
    s.addText(name, T({ x: x + 1.1, y: 2.3, w: 2.4, h: 0.45, fontSize: 19, bold: true, color: col }));
    s.addText(...bulletList(pts, { x: x + 0.35, y: 3.1, w: 3.15, h: 3.35, fontSize: 15, paraSpaceAfter: 7 }));
    if (i < 2) s.addShape(pres.shapes.LINE, { x: x + 3.75, y: 4.27, w: 0.4, h: 0,
      line: { color: HEX.ink, width: 2, endArrowType: "triangle" } });
  }
  say(s, P.aditya, 75, "Data and labels",
    "Our test set is the official IMDb benchmark: 25,000 movie reviews that we never change, so " +
    "our numbers are comparable with published work. We split the official 25,000 training reviews into 20,000 for " +
    "training and 5,000 for validation. To train bigger and better models we built an extra pool. We started from " +
    "5.5 million scraped IMDb reviews and 17.3 million Amazon Movies and TV reviews. We labelled them with the " +
    "standard IMDb rule: 4 out of 10 or less is negative, 7 or more is positive, and the middle is dropped. For " +
    "Amazon it is one or two stars against four or five. After removing duplicates we had 4.1 million IMDb and 12 " +
    "million Amazon reviews. The clean IMDb pool was then split three ways: 1.53 million for training, 300,000 held " +
    "out for the deferral experiments, and a 50,000-review validation pool drawn from movies no model trains on.");

  // 8. Leakage
  s = talk("Part 1: Problem, idea and data", "Data without leakage", P.aditya,
    "We removed every way test reviews could leak into training",
    "Official IMDb test set (25,000 reviews) is scored once; every threshold is chosen on validation data");
  const stats = [
    ["4.1M", "clean IMDb reviews in the extra pool", "from 5.5M scraped (plus 12.0M Amazon)", "FaDatabase"],
    ["23,818", "copies of test or validation reviews removed", "exact matches after normalising text", "FaCopy"],
    ["635,853", "reviews by test-set authors removed", "plus 163,409 reviews of test-set movies", "FaUserSlash"],
    ["0", "deferral-slice reviews in hub training", "an older slice overlapped 31%; we re-drew it", "FaShieldAlt"],
  ];
  for (let i = 0; i < stats.length; i++) {
    await statCard(s, 0.6 + i * 3.075, 1.95, 2.85, 4.6, stats[i][0], stats[i][1], stats[i][2],
      i === 3 ? C.accent3 : C.accent2, stats[i][3]);
  }
  say(s, P.aditya, 75, "Data without leakage",
    "The danger with scraped data is that it contains the test set. About 2.9 percent of IMDb test labels are " +
    "wrong, so honest accuracy tops out around 97 percent; a result near 99 usually means leakage. So we removed " +
    "every route we could find: 23,818 exact copies of test or validation reviews; every review written by an " +
    "author who also wrote a test review, which is 635,853 reviews; another 163,409 reviews of the movies in the " +
    "test set; and near-duplicates, meaning edited reposts that share 30 percent or more of a test review's " +
    "eight-word sequences. One more catch: when we retrained the hub, we found that 31 percent of our old deferral " +
    "slice was inside the new hub's training data. Labels from it would have been too optimistic, so we drew a new " +
    "slice and verified it has zero overlap. Danyson will now take you through the models we trained on it.");

  // 9. Device model
  pres.addSection({ title: "Part 2: Models and learned deferral" });
  s = talk("Part 2: Models and learned deferral", "The device model", P.danyson,
    "A 256 KB model that is just a table of 8-bit weights",
    "Validation accuracy of the 256 KB int8 model (device v1) as the training set grows; Naive Bayes weighting: Wang & Manning 2012");
  card(s, 0.6, 1.95, 5.9, 4.75, C.background2, "how it works");
  s.addText("How it reads a review", T({ x: 0.95, y: 2.2, w: 5.2, h: 0.45, fontSize: 19, bold: true, color: C.accent2 }));
  const steps = ["Split into words and word pairs", "Hash each into one of 262,144 buckets",
    "Add up the buckets' int8 weights, divide by √n", "Sigmoid turns the sum into p(x)"];
  for (let i = 0; i < steps.length; i++) {
    const y = 2.8 + i * 0.55;
    s.addShape(pres.shapes.OVAL, { x: 0.95, y, w: 0.4, h: 0.4, fill: { color: C.accent1 }, line: { type: "none" } });
    s.addText(String(i + 1), T({ x: 0.95, y, w: 0.4, h: 0.4, fontSize: 14, bold: true, color: C.background1,
      align: "center", valign: "middle" }));
    s.addText(steps[i], T({ x: 1.5, y, w: 4.8, h: 0.4, fontSize: 15, color: C.text1, valign: "middle" }));
  }
  s.addText("p(x) = σ( 0.3075 × Σ q_b / √n + 0.0152 )", T({ x: 0.95, y: 5.1, w: 5.3, h: 0.45, fontFace: "Cambria",
    fontSize: 17, bold: true, color: C.accent3 }));
  s.addText("Trained with Naive Bayes weighting and logistic loss, averaged SGD for 5 passes, then rounded to int8",
    T({ x: 0.95, y: 5.65, w: 5.3, h: 0.85, fontSize: 14, italic: true, color: C.text1, valign: "top" }));
  const curve = CHIP.size_curve;
  const sizeLabel = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(n % 1e6 ? 2 : 0)}M` : `${n / 1000}k`);
  s.addChart(pres.charts.BAR, [{ name: "Validation accuracy (%)", labels: curve.map((r) => sizeLabel(r.train_reviews)),
    values: curve.map((r) => +(r.val_accuracy_int8 * 100).toFixed(2)) }], {
    x: 6.8, y: 1.85, w: 5.9, h: 4.85, barDir: "col", chartColors: [HEX.sage], valAxisMinVal: 89, valAxisMaxVal: 93.5,
    valAxisMajorUnit: 1, showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", showLegend: false,
    barGapWidthPct: 55, showCatAxisTitle: true, catAxisTitle: "Training reviews", showValAxisTitle: true,
    valAxisTitle: "Validation accuracy (%)", objectName: "device size curve", ...chartText(),
  });
  say(s, P.danyson, 75, "The device model",
    "The device model is deliberately simple, because it has to run on a microcontroller. It takes every word and " +
    "every pair of adjacent words, hashes each into one of 262,144 buckets, and adds up the 8-bit weight stored for " +
    "each bucket. Dividing by the square root of the number of buckets evens out long and short reviews, and a " +
    "sigmoid turns the sum into a probability. The whole model is those 262,144 weights, which is 256 kilobytes, " +
    "plus one scale and one bias. Training uses Naive Bayes feature weighting and logistic loss, optimised with " +
    "averaged stochastic gradient descent for five passes, and the weights are then rounded to 8 bits. The chart " +
    "shows why the data matters: validation accuracy climbs from 90.2 percent with 20,000 reviews to 92.8 percent " +
    "with 1.94 million.");

  // 10. Hub training
  s = talk("Part 2: Models and learned deferral", "Training the hub", P.danyson,
    "Retraining the hub on one million extra reviews",
    "Settings from the saved run metrics; costs from Modal's billing report; H100 = $3.95 per hour");
  const th = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.accent1 }, align: "center" } });
  const tc = (t, o = {}) => ({ text: t, options: { align: "center", ...o } });
  s.addTable([
    [th("Hub"), th("Training reviews"), th("Epochs"), th("Batch"), th("Learning rate"), th("Hardware"), th("Speed"), th("Cost")],
    [{ text: "DistilBERT, 20k", options: { bold: true } }, tc("20,000"), tc("2"), tc("16"), tc("3 × 10⁻⁵"),
      tc("Laptop GPU (M3 Pro)"), tc("47 min total"), tc("free")],
    [{ text: "DistilBERT, +1M", options: { bold: true } }, tc("1,020,000"), tc("1"), tc("32"), tc("3 × 10⁻⁵"),
      tc("NVIDIA H100"), tc("≈2,240 reviews/s"), tc("$0.91")],
    [{ text: "RoBERTa-base, +1M", options: { bold: true } }, tc("1,020,000"), tc("1"), tc("32"), tc("2 × 10⁻⁵"),
      tc("NVIDIA H100"), tc("≈1,170 reviews/s"), tc("$1.64")],
  ], { x: 0.6, y: 1.95, w: 12.1, colW: [2.0, 1.55, 0.95, 0.85, 1.4, 2.15, 1.85, 1.35], fontSize: 14, color: HEX.ink,
    fontFace: "Calibri", border: { type: "solid", pt: 0.75, color: HEX.grid }, fill: { color: HEX.blush }, rowH: 0.55,
    valign: "middle", objectName: "hub training table" });
  card(s, 0.6, 4.55, 12.1, 2.1, C.accent4, "shared recipe");
  s.addText("Shared recipe for the +1M runs", T({ x: 0.9, y: 4.7, w: 11.5, h: 0.4, fontSize: 17, bold: true, color: C.accent3 }));
  s.addText(...bulletList([
    "1,020,000 ÷ 32 = 31,875 optimiser steps; AdamW, warm-up over the first 6%, then linear decay; bfloat16",
    "Reviews over 512 tokens keep their first 128 and last 382 tokens; similar lengths are batched together",
    "Every 2,000 steps, check accuracy on the 50k val_pool and keep the best checkpoint (never validation or test)",
  ], { x: 0.9, y: 5.15, w: 11.5, h: 1.4, fontSize: 15, paraSpaceAfter: 4 }));
  say(s, P.danyson, 75, "Training the hub",
    "For the hub we trained transformers. The original hub was DistilBERT fine-tuned on just the 20,000 official " +
    "reviews: two epochs on a laptop GPU, 47 minutes, and free. For the paper we retrained the hub on 1,020,000 " +
    "reviews: those 20,000 plus one million from the clean pool. We trained both DistilBERT and RoBERTa-base, each " +
    "for one epoch with a batch size of 32, which is 31,875 optimiser steps. We used AdamW with a 6 percent " +
    "warm-up and bfloat16 precision, and long reviews keep their first 128 and last 382 tokens. Every 2,000 steps " +
    "we checked accuracy on the 50,000-review validation pool and kept the best checkpoint. Both ran on a single " +
    "NVIDIA H100 in the cloud: DistilBERT at about 2,240 reviews a second, RoBERTa-base at about 1,170.");

  // 11. Models
  s = talk("Part 2: Models and learned deferral", "The models", P.danyson, "More leak-free training data lifted every model",
    "Official IMDb test set; the ensemble (ELECTRA-large + DeBERTa-v3-large + 1 MB n-gram) is a reference ceiling, too big for the hub");
  const models = [["TF-IDF + LR (20k)", 90.28], ["Device, 256 KB", 92.69], ["DistilBERT, 20k", 93.51],
    ["DistilBERT, +1M", 95.83], ["RoBERTa-base, +1M", 96.72], ["Ensemble, +1M", 97.40]];
  s.addChart(pres.charts.BAR, [{ name: "Test accuracy (%)", labels: models.map((m) => m[0]), values: models.map((m) => m[1]) }], {
    x: 0.6, y: 1.85, w: 7.6, h: 4.9, barDir: "bar", chartColors: [HEX.mauve, HEX.sage, HEX.mauve, HEX.rose, HEX.rose, HEX.muted],
    valAxisMinVal: 88, valAxisMaxVal: 98, valAxisMajorUnit: 2, showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.00", showLegend: false, catAxisOrientation: "maxMin", barGapWidthPct: 45,
    showTitle: false, objectName: "model accuracy chart", ...chartText(),
  });
  const modelStats = [
    ["+2.3 pts", "DistilBERT with 1M extra reviews", C.accent2],
    ["97.40%", "ensemble: above the best peer-reviewed 97.1%", C.accent3],
    ["24,180", "of 25,000 test reviews right with RoBERTa-base", C.accent1],
  ];
  for (let i = 0; i < modelStats.length; i++) { // compact cards: three fit beside the chart
    const y = 1.95 + i * 1.6, [big, label, col] = modelStats[i];
    card(s, 8.6, y, 4.1, 1.4, C.background2, `stat ${big}`);
    s.addText(big, T({ x: 8.9, y: y + 0.15, w: 3.5, h: 0.6, fontFace: "Cambria", fontSize: 30, bold: true,
      color: col, valign: "middle" }));
    s.addText(label, T({ x: 8.9, y: y + 0.78, w: 3.5, h: 0.5, fontSize: 14, bold: true, color: C.text2, valign: "top" }));
  }
  say(s, P.danyson, 60, "The models",
    "Here is what that bought us, all on the official test set, where accuracy is simply the number right out of " +
    "25,000. TF-IDF with logistic regression gets 90.3 percent. Our 256-kilobyte device model gets 92.7. DistilBERT " +
    "on 20,000 reviews gets 93.5; with the extra million it gets 95.8, a gain of 2.3 points. RoBERTa-base reaches " +
    "96.7 percent, which is 24,180 reviews out of 25,000. For reference, an ensemble of two large models plus our " +
    "n-gram model reaches 97.4 percent, above the best peer-reviewed result of 97.1, in the extra-training-data " +
    "setting. It is far too big for the hub; it simply shows the ceiling.");

  // 12. Cost
  s = talk("Part 2: Models and learned deferral", "Compute cost", P.danyson, "The whole project cost $20.27 of cloud GPU time",
    "Itemised per run with `modal billing report`; paid from Modal credits, so $0 was billed. Every run had a hard time cap.");
  s.addChart(pres.charts.BAR, [{ name: "Cost (USD)", labels: COSTS.map((c) => c[0]), values: COSTS.map((c) => c[1]) }], {
    x: 0.5, y: 1.85, w: 7.7, h: 4.9, barDir: "bar", chartColors: [HEX.muted, HEX.muted, HEX.muted, HEX.rose, HEX.rose,
      HEX.muted, HEX.muted, HEX.muted], valAxisMinVal: 0, valAxisMaxVal: 10, valAxisMajorUnit: 2, showValue: true,
    dataLabelPosition: "outEnd", dataLabelFormatCode: "\"$\"0.00", showLegend: false, catAxisOrientation: "maxMin",
    barGapWidthPct: 40, objectName: "cost chart", ...chartText(),
  });
  const costStats = [
    ["$2.56", "retraining both hubs (paper)", C.accent2],
    ["$17.71", "large record-attempt models", C.accent1],
    ["$0", "laptop work: device model, routers, analysis", C.accent3],
  ];
  for (let i = 0; i < costStats.length; i++) {
    const y = 1.95 + i * 1.6, [big, label, col] = costStats[i];
    card(s, 8.6, y, 4.1, 1.4, C.background2, `cost ${big}`);
    s.addText(big, T({ x: 8.9, y: y + 0.15, w: 3.5, h: 0.6, fontFace: "Cambria", fontSize: 30, bold: true,
      color: col, valign: "middle" }));
    s.addText(label, T({ x: 8.9, y: y + 0.78, w: 3.5, h: 0.5, fontSize: 14, bold: true, color: C.text2, valign: "top" }));
  }
  say(s, P.danyson, 60, "Compute cost",
    "And here is what it cost. We itemised every cloud run from Modal's billing report. Retraining the two hubs " +
    "for this paper cost 2 dollars 56: RoBERTa-base 1 dollar 64, DistilBERT 91 cents and tokenising 2 cents. " +
    "RoBERTa-base reused RoBERTa-large's cached tokens, because the two split text identically, which saved a run. " +
    "The large record-attempt models cost 17 dollars 71, most of it DeBERTa-v3-large at 9 dollars. Every run had a " +
    "hard time limit, so none could overrun its budget, and everything was paid from free credits, so nothing was " +
    "billed. The device model, the deferral models and all the analysis ran free on a laptop. Next, the router that decides what to send.");

  // 13. Deferral training
  s = talk("Part 2: Models and learned deferral", "Training the router", P.danyson,
    "Learned deferral is trained on 300,000 reviews both models have answered",
    "Counts for the RoBERTa-base hub on the re-drawn deferral slice; regularisation chosen at 10% sent (C = 0.1)");
  const gains = [["+1", "16,276", "hub fixes the device (5.43%)", C.accent3], ["0", "279,992", "no change (93.33%)", C.accent1],
    ["−1", "3,732", "hub breaks the device (1.24%)", C.accent2]];
  for (let i = 0; i < gains.length; i++) {
    const x = 0.6 + i * 4.1, [g, n, label, col] = gains[i];
    card(s, x, 1.95, 3.8, 1.75, C.background2, `gain ${g}`);
    s.addText(g, T({ x: x + 0.3, y: 2.15, w: 0.9, h: 0.75, fontFace: "Cambria", fontSize: 34, bold: true, color: col,
      valign: "middle" }));
    s.addText(n, T({ x: x + 1.25, y: 2.15, w: 2.3, h: 0.75, fontFace: "Cambria", fontSize: 30, bold: true,
      color: C.text2, valign: "middle" }));
    s.addText(label, T({ x: x + 0.3, y: 3.0, w: 3.3, h: 0.5, fontSize: 15, color: C.text1 }));
  }
  card(s, 0.6, 4.0, 5.9, 2.65, C.background2, "features");
  s.addText("What the router sees (fits the device)", T({ x: 0.9, y: 4.2, w: 5.4, h: 0.4, fontSize: 17, bold: true, color: C.accent2 }));
  s.addText(...bulletList(["65,536 hashed word buckets; two int8 tables = 128 KB", "Device confidence in 10 bins (0.5 to 1.0)",
    "Review length in 9 bins"], { x: 0.9, y: 4.75, w: 5.4, h: 1.8, fontSize: 15 }));
  card(s, 6.8, 4.0, 5.9, 2.65, C.background2, "model");
  s.addText("How it is trained and used", T({ x: 7.1, y: 4.2, w: 5.4, h: 0.4, fontSize: 17, bold: true, color: C.accent3 }));
  s.addText(...bulletList(["Gain = hub right − device right", "3-class logistic regression on 250,000 reviews",
    "Score: g(x) = P(+1) − P(−1)"], { x: 7.1, y: 4.75, w: 5.4, h: 1.8, fontSize: 15 }));
  say(s, P.danyson, 75, "Training the router",
    "To train the learned router we need labels, and that is what the held-out 300,000 reviews " +
    "are for: both the device and the hub have answered every one of them, and neither was trained on them. For " +
    "each review, the gain is the hub being right minus the device being right. With the RoBERTa-base hub, 16,276 " +
    "reviews are fixes, plus one; 3,732 are breaks, minus one; and 279,992 do not change. The router only sees what " +
    "the device can compute: 65,536 hashed word buckets, plus the device's confidence in ten bins and the review " +
    "length in nine. On the device that is two 8-bit weight tables, 128 kilobytes in all. It is a three-class logistic regression trained on 250,000 reviews, with " +
    "its regularisation chosen on the other 50,000. Its score, g of x, is the probability of a fix minus the " +
    "probability of a break.");

  // 14. Worked example
  const ex = { thr: 0.255, sent: 2625, fixed: 832, broken: 127, right: 1522, wrong: 144, device: 23079 };
  s = talk("Part 2: Models and learned deferral", "How every number is computed", P.danyson,
    "One operating point, from threshold to accuracy",
    "RoBERTa-base hub, confidence routing, 10% target; device v2 alone gets 23,079 of 25,000 test reviews right");
  const work = [
    ["Pick the threshold on validation", "90th percentile of the 5,000 validation scores = 0.255, so send when the device's confidence is below 0.745"],
    ["Apply it to the test set once", `It sends ${ex.sent.toLocaleString("en-US")} of 25,000 reviews (10.50%)`],
    ["Count right answers", `(${ex.device.toLocaleString("en-US")} + ${ex.fixed} − ${ex.broken}) ÷ 25,000 = 95.14%`],
  ];
  for (let i = 0; i < work.length; i++) {
    const y = 1.95 + i * 1.55;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.6, h: 0.6, fill: { color: C.accent2 }, line: { type: "none" } });
    s.addText(String(i + 1), T({ x: 0.6, y, w: 0.6, h: 0.6, fontFace: "Cambria", fontSize: 22, bold: true,
      color: C.background1, align: "center", valign: "middle" }));
    s.addText(work[i][0], T({ x: 1.4, y: y - 0.02, w: 5.6, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
    s.addText(work[i][1], T({ x: 1.4, y: y + 0.45, w: 5.6, h: 0.85, fontSize: 15, color: C.text1, valign: "top" }));
  }
  s.addChart(pres.charts.DOUGHNUT, [{ name: "The 2,625 reviews sent", labels: [`Hub fixes: ${ex.fixed}`,
    `Hub breaks: ${ex.broken}`, `Already right: ${ex.right.toLocaleString("en-US")}`, `Wrong either way: ${ex.wrong}`],
    values: [ex.fixed, ex.broken, ex.right, ex.wrong] }], { // counts live in the legend: labels on thin slices are unreadable
    x: 7.4, y: 1.8, w: 5.3, h: 4.9, holeSize: 55, chartColors: [HEX.sage, HEX.rose, HEX.muted, HEX.mauve],
    showValue: false, showPercent: false, showLegend: true, legendPos: "r",
    showTitle: true, title: "The 2,625 reviews sent", titleFontSize: 15, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    objectName: "sent breakdown", ...chartText(), legendFontSize: 13,
  });
  say(s, P.danyson, 90, "How every number is computed",
    "Every threshold is chosen on validation data and applied to the test set exactly once. Here is one operating " +
    "point worked through: the RoBERTa-base hub, confidence routing, aiming to send 10 percent. Step one: take the " +
    "90th percentile of the scores on the 5,000 validation reviews. That is 0.255, which means: send a review when " +
    "the device's confidence is below 0.745. Step two: apply that threshold to the 25,000 test reviews. It sends " +
    "2,625 of them, 10.5 percent. Of those, the hub fixes 832 and breaks 127; 1,522 were already right and 144 are " +
    "wrong either way. Step three: the device alone gets 23,079 right, so the accuracy is 23,079 plus 832 minus 127, " +
    "divided by 25,000, which is 95.14 percent. Every number in our tables is computed exactly this way.");

  // 15. Main result chart
  s = talk("Part 2: Models and learned deferral", "Main result", P.danyson,
    "Learned deferral matches confidence routing, but doesn't beat it",
    "Hub: RoBERTa-base trained with 1M extra reviews; test-set curves (operating points on the next slide use validation thresholds)");
  const cv = DEFER.roberta.curves_test;
  const idx = cv.rates.map((r, i) => i).filter((i) => cv.rates[i] <= 0.6001);
  const lab = idx.map((i) => String(Math.round(cv.rates[i] * 100)));
  const hubAcc = DEFER.roberta.hub_test_accuracy * 100;
  const series = (name, key) => ({ name, labels: lab, values: idx.map((i) => +(cv[key][i] * 100).toFixed(3)) });
  const lineOpts = (colors, dash) => ({ chartColors: colors, lineSize: 2.75, lineDash: dash, lineDataSymbol: "none" });
  s.addChart([ // one line group per dash style: pptxgenjs sets the dash for a whole group
    { type: pres.charts.LINE, data: [series("Confidence routing", "confidence"),
      { name: "Hub alone", labels: lab, values: idx.map(() => +hubAcc.toFixed(3)) }],
      options: lineOpts([HEX.rose, HEX.mauve], "solid") },
    { type: pres.charts.LINE, data: [series("Learned deferral", "learned")], options: lineOpts([HEX.sage], "dash") },
    { type: pres.charts.LINE, data: [series("Perfect router", "oracle")], options: lineOpts([HEX.muted], "sysDot") },
  ], {
    x: 0.5, y: 1.8, w: 8.1, h: 5.0, valAxisMinVal: 92, valAxisMaxVal: 98, valAxisMajorUnit: 1, catAxisLabelFrequency: 10,
    showLegend: true, legendPos: "b", showCatAxisTitle: true, catAxisTitle: "Reviews sent to the hub (%)",
    showValAxisTitle: true, valAxisTitle: "Test accuracy (%)", objectName: "routing curves", ...chartText(),
  });
  await statCard(s, 8.95, 1.95, 3.75, 2.2, "≤ 0.14 pts", "largest gap at the tested send rates, across 3 hubs", null, C.accent2);
  await statCard(s, 8.95, 4.4, 3.75, 2.2, "0 of 15", "differences significant after Bonferroni correction", null, C.accent3);
  say(s, P.danyson, 75, "Main result",
    "Now the main result. This chart sweeps the share of reviews sent, from 0 to 60 percent, with the RoBERTa-base " +
    "hub. The solid red line is confidence routing and the dashed green line is learned deferral. They lie on top of " +
    "each other across the whole range. The dotted grey line is a perfect router that sends exactly the reviews the " +
    "hub fixes. It reaches 97.3 percent at just 5 percent sent, so there is real room to improve; learned deferral " +
    "just does not find it. Across all three hubs, the largest gap at any tested operating point is 0.14 points, " +
    "and after correcting for running 15 tests, not one difference is significant. Ehsan will show you that this " +
    "holds for every hub.");

  // 16. Table across hubs
  pres.addSection({ title: "Part 3: Results, energy and conclusions" });
  s = talk("Part 3: Results, energy and conclusions", "All three hubs", P.ehsan, "The same picture holds for every hub we tried",
    "Thresholds chosen on validation data; exact McNemar test on 25,000 paired test predictions; Bonferroni level 0.05 ÷ 15 = 0.0033");
  const head = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.accent1 }, align: "center" } });
  const rows = [[head("Hub (accuracy alone)"), head("10% sent: confidence"), head("10% sent: learned"), head("p"),
    head("20% sent: confidence"), head("20% sent: learned"), head("p")]];
  const hubs = [["DistilBERT, 20k (93.51%)", DEFER.weak], ["DistilBERT, +1M (95.83%)", DEFER.distil],
    ["RoBERTa-base, +1M (96.72%)", DEFER.roberta]];
  for (const [name, d] of hubs) {
    const op = d.operating_points_test, m = d.learned_vs_confidence_mcnemar;
    const cell = (t, o = {}) => ({ text: t, options: { align: "center", ...o } });
    rows.push([{ text: name, options: { bold: true } },
      cell(pct(op.confidence["10%"].accuracy)), cell(pct(op.learned["10%"].accuracy)), cell(m["10%"].p_value.toFixed(2)),
      cell(pct(op.confidence["20%"].accuracy)), cell(pct(op.learned["20%"].accuracy)), cell(m["20%"].p_value.toFixed(2))]);
  }
  s.addTable(rows, { x: 0.6, y: 1.95, w: 12.1, colW: [3.1, 1.65, 1.55, 0.95, 1.65, 1.55, 1.65],
    fontSize: 15, color: HEX.ink, fontFace: "Calibri", border: { type: "solid", pt: 0.75, color: HEX.grid },
    fill: { color: HEX.blush }, rowH: 0.55, valign: "middle", objectName: "router comparison table" });
  const mc = DEFER.roberta.learned_vs_confidence_mcnemar["10%"];
  card(s, 0.6, 4.45, 12.1, 2.2, C.accent4, "mcnemar worked");
  s.addText([
    { text: "The test, worked through (RoBERTa-base, 10% sent)", options: { bold: true, color: C.accent3, breakLine: true } },
    { text: `${mc.a_only_right} reviews are right only with learned deferral, ${mc.b_only_right} only with confidence ` +
      `routing. If the routers were equal these would split 50/50; seeing ${mc.b_only_right} or fewer of ` +
      `${mc.a_only_right + mc.b_only_right} has two-sided probability p = ${mc.p_value.toFixed(3)}. That is above the ` +
      "corrected level of 0.0033, so it is not significant, and part of the gap comes from sending 10.7% instead of 10.5%.",
      options: { color: C.text1 } },
  ], T({ x: 0.9, y: 4.45, w: 11.5, h: 2.2, fontSize: 16, valign: "middle", paraSpaceAfter: 6 }));
  say(s, P.ehsan, 75, "All three hubs",
    "Thank you, Danyson. Here are the operating points for all three hubs at 10 and 20 percent sent. Read across each row: confidence " +
    "and learned land within about a tenth of a point. To test that properly we use the exact McNemar test on the " +
    "paired predictions. Take RoBERTa-base at 10 percent: 68 reviews are right only with learned deferral and 44 " +
    "only with confidence routing. If the two routers were equal, those would split 50-50; getting 44 or fewer out " +
    "of 112 has a two-sided probability of 0.029. That looks significant, but we ran 15 such tests, so the " +
    "Bonferroni threshold is 0.05 divided by 15, which is 0.0033, and 0.029 does not pass. Part of that gap also " +
    "comes from learned deferral sending 10.7 percent of reviews instead of 10.5.");

  // 17. Why
  s = talk("Part 3: Results, energy and conclusions", "Why it doesn't help", P.ehsan,
    "A stronger hub rarely breaks a correct answer, so there is little to avoid",
    "Shares of the 300,000-review deferral slice; breakdown at 10% sent is for the RoBERTa-base hub on the test set");
  const fb = [DEFER.weak, DEFER.distil, DEFER.roberta].map((d) => d.deferral_slice);
  s.addChart(pres.charts.BAR, [
    { name: "Hub fixes the device", labels: ["DistilBERT, 20k", "DistilBERT, +1M", "RoBERTa-base, +1M"],
      values: fb.map((f) => +(f.fixable * 100).toFixed(1)) },
    { name: "Hub breaks the device", labels: ["DistilBERT, 20k", "DistilBERT, +1M", "RoBERTa-base, +1M"],
      values: fb.map((f) => +(f.breakable * 100).toFixed(1)) },
  ], {
    x: 0.5, y: 1.8, w: 6.9, h: 5.0, barDir: "col", barGrouping: "clustered", chartColors: [HEX.sage, HEX.rose],
    valAxisMinVal: 0, valAxisMaxVal: 6, valAxisMajorUnit: 1, showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0\"%\"", showLegend: true, legendPos: "b", barGapWidthPct: 60,
    showValAxisTitle: true, valAxisTitle: "Share of device answers (%)", objectName: "fix break chart", ...chartText(),
  });
  const rb = DEFER.roberta.operating_points_test;
  const why = [
    ["FaCheckCircle", C.accent3, `${pct(rb.confidence["10%"].sent_already_right, 0)}% already right`,
      "of what either router sends at 10%; learned deferral doesn't lower it"],
    ["FaTimesCircle", C.accent2, `${pct(rb.confidence["10%"].sent_broken, 1)}% would break`,
      "so avoiding breaks, the easy win, is almost gone"],
    ["FaBullseye", C.accent1, `${pct(DEFER.roberta.curves_test.oracle[5], 1)}% possible`,
      "a perfect router at 5% sent: 128 KB of word buckets can't find which reviews the hub fixes"],
  ];
  for (let i = 0; i < why.length; i++) {
    const y = 1.95 + i * 1.6;
    await iconCircle(s, 7.8, y + 0.1, 0.7, why[i][0], why[i][1]);
    s.addText(why[i][2], T({ x: 8.7, y, w: 4.0, h: 0.5, fontFace: "Cambria", fontSize: 22, bold: true, color: why[i][1] }));
    s.addText(why[i][3], T({ x: 8.7, y: y + 0.5, w: 4.0, h: 0.85, fontSize: 15, color: C.text1, valign: "top" }));
  }
  say(s, P.ehsan, 75, "Why it doesn't help",
    "So why doesn't it help? Learned deferral can win in two ways: by not sending reviews the hub would break, or by " +
    "finding the reviews the hub would fix. Look at the chart. The weak 20,000-review hub breaks almost as many " +
    "answers as it fixes: 3.9 percent against 4.1. The retrained hubs break only 1.2 to 1.5 percent, so the first " +
    "kind of win has nearly disappeared. At 10 percent sent with RoBERTa-base, 58 percent of what either router " +
    "sends was already right, and learned deferral does not reduce that. The second kind of win needs to know where " +
    "the hub is right, and 128 kilobytes of word buckets carry little information about that beyond the device's own " +
    "confidence. Next, what this means for energy.");

  // 18. Energy model
  s = talk("Part 3: Results, energy and conclusions", "The energy model", P.ehsan,
    "Every send costs the device about 300 mJ; answering locally costs under 1 mJ",
    "Currents: ESP32-S3 datasheet v2.2 (240 MHz one core; 802.11n MCS7 at 18.5 dBm; RX). Timings are placeholders until measured.");
  card(s, 0.6, 1.95, 12.1, 1.2, C.accent4, "formula");
  s.addText("E(s) = V × [ I_cpu × t_local  +  s × ( I_tx × t_tx  +  I_rx × t_wait ) ]", T({ x: 0.9, y: 1.95, w: 11.5,
    h: 1.2, fontFace: "Cambria", fontSize: 26, bold: true, color: C.accent3, align: "center", valign: "middle" }));
  const eparts = [
    ["Answer on the device", "3.3 V × 51.2 mA × 5 ms", "0.84 mJ", C.accent3],
    ["Each send to the hub", "3.3 V × (283 mA × 10 ms\n+ 88 mA × 1 s)", "299.74 mJ", C.accent2],
    ["Send every review", "0.84 + 1.0 × 299.74", "300.58 mJ", C.accent1],
  ];
  for (let i = 0; i < eparts.length; i++) {
    const x = 0.6 + i * 4.1, [name, calc, val, col] = eparts[i];
    card(s, x, 3.45, 3.8, 3.2, C.background2, name);
    s.addText(name, T({ x: x + 0.3, y: 3.7, w: 3.2, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
    s.addText(calc, T({ x: x + 0.3, y: 4.25, w: 3.2, h: 0.85, fontSize: 15, color: C.text1, valign: "top" }));
    s.addText(val, T({ x: x + 0.3, y: 5.3, w: 3.2, h: 0.9, fontFace: "Cambria", fontSize: 34, bold: true, color: col,
      valign: "middle" }));
  }
  say(s, P.ehsan, 75, "The energy model",
    "To turn send rates into battery use, we model the device's energy per review. Every review " +
    "costs the device's own computation: 3.3 volts times 51.2 milliamps for 5 milliseconds, which is 0.84 " +
    "millijoules. Each review it sends adds the radio: 283 milliamps for 10 milliseconds to transmit, plus 88 " +
    "milliamps for about one second of listening while the hub answers. That is 299.7 millijoules per send. So the " +
    "energy per review is 0.84 plus the share sent times 299.7, and sending everything costs 300.6 millijoules. The " +
    "currents come from the ESP32-S3 datasheet; the three timings are placeholders until we measure them on the " +
    "board.");

  // 19. Energy results
  s = talk("Part 3: Results, energy and conclusions", "Energy results", P.ehsan,
    "Sending one review in six closes three quarters of the accuracy gap",
    "Targets chosen on validation data, then applied once to test; RoBERTa-base hub; 1 s hub wait (placeholder)");
  const rob = ENERGY.rows.filter((r) => r.hub.startsWith("RoBERTa"));
  const eLabels = ["Device only", ...rob.map((r) => `Close ${Math.round(r.gap_share * 100)}% of gap`), "Send everything"];
  const eVals = [ENERGY.chip_only_mJ, ...rob.map((r) => r.mJ), ENERGY.send_all_mJ].map((v) => +v.toFixed(1));
  s.addChart(pres.charts.BAR, [{ name: "mJ per review", labels: eLabels, values: eVals }], {
    x: 0.5, y: 1.8, w: 7.4, h: 5.0, barDir: "col", chartColors: [HEX.sage, HEX.mauve, HEX.mauve, HEX.mauve, HEX.rose],
    valAxisMinVal: 0, valAxisMaxVal: 350, valAxisMajorUnit: 50, showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0", showLegend: false, barGapWidthPct: 50, showValAxisTitle: true,
    valAxisTitle: "Device energy per review (mJ)", objectName: "energy chart", ...chartText(),
  });
  const quarter = rob.find((r) => r.gap_share === 0.75);
  card(s, 8.3, 1.95, 4.4, 4.7, C.background2, "worked energy");
  s.addText("Worked: close 75% of the gap", T({ x: 8.6, y: 2.15, w: 3.9, h: 0.45, fontSize: 18, bold: true, color: C.accent2 }));
  s.addText(...bulletList([
    "Target on validation: 92.56 + 0.75 × 3.90 = 95.485%",
    "Needs 16% sent on validation",
    `On test: ${pct(quarter.test_sent, 1)}% sent, ${pct(quarter.test_accuracy)}% accurate`,
    `Energy: 0.84 + 0.169 × 299.74 = ${quarter.mJ.toFixed(1)} mJ`,
    `300.58 ÷ ${quarter.mJ.toFixed(2)} = ${quarter.saving_vs_send_all.toFixed(1)}× less than sending all`,
  ], { x: 8.6, y: 2.75, w: 3.9, h: 3.8, fontSize: 15, paraSpaceAfter: 7 }));
  say(s, P.ehsan, 75, "Energy results",
    "Here is what that gives with the RoBERTa-base hub, with every target chosen on validation data. To close half " +
    "the gap between the device and the hub, we send about 8 percent of reviews, at 25.8 millijoules: about 12 " +
    "times less than sending everything. For three quarters of the gap, the target on validation is 92.56 plus " +
    "three quarters of the 3.9-point gap, which is about 95.5 percent. That needs 16 percent sent on validation, which " +
    "on test sends 16.9 percent and scores 95.89. The energy is 0.84 plus 0.169 times 299.7, which is 51.5 " +
    "millijoules, 5.8 times less than sending everything. Matching the hub exactly needs most reviews sent, so the " +
    "savings are in the middle of the curve.");

  // 20. Battery
  s = talk("Part 3: Results, energy and conclusions", "What it means for a battery", P.ehsan,
    "Closing three quarters of the gap gives almost 6× more reviews per charge than sending everything",
    "Illustrative 2,000 mAh, 3.7 V cell = 26,640 J; energy per review only (idle and sleep power not included)");
  const per = (mj) => BATTERY_J / (mj / 1000);
  const fmtN = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(n >= 1e7 ? 1 : 2)}M` : `${Math.round(n / 1000)}k`);
  const battery = [
    ["Device only", ENERGY.chip_only_mJ, "92.32% accurate", C.accent3],
    ["Close 50% of gap", rob[0].mJ, `${pct(rob[0].test_accuracy)}% accurate`, C.accent1],
    ["Close 75% of gap", quarter.mJ, `${pct(quarter.test_accuracy)}% accurate`, C.accent2],
    ["Send everything", ENERGY.send_all_mJ, "96.72% accurate", C.accent6],
  ];
  for (let i = 0; i < battery.length; i++) {
    const x = 0.6 + i * 3.075, [name, mj, acc, col] = battery[i];
    card(s, x, 1.95, 2.85, 3.6, C.background2, name);
    s.addText(name, T({ x: x + 0.3, y: 2.2, w: 2.3, h: 0.45, fontSize: 17, bold: true, color: C.text2 }));
    s.addText(fmtN(per(mj)), T({ x: x + 0.3, y: 2.8, w: 2.3, h: 0.9, fontFace: "Cambria", fontSize: 38, bold: true,
      color: col, valign: "middle" }));
    s.addText("reviews per charge", T({ x: x + 0.3, y: 3.7, w: 2.3, h: 0.35, fontSize: 14, color: C.text1 }));
    s.addText(`${mj.toFixed(1)} mJ each · ${acc}`, T({ x: x + 0.3, y: 4.45, w: 2.3, h: 0.85, fontSize: 13,
      color: C.accent6, valign: "top" }));
  }
  card(s, 0.6, 5.8, 12.1, 0.85, C.accent4, "battery formula");
  s.addText([
    { text: "Reviews per charge = 26,640 J ÷ energy per review", options: { bold: true, color: C.accent3 } },
    { text: `     e.g. 26,640 ÷ 0.05151 J = ${Math.round(per(quarter.mJ)).toLocaleString("en-US")}`, options: { color: C.text1 } },
  ], T({ x: 0.9, y: 5.8, w: 11.5, h: 0.85, fontSize: 16, valign: "middle" }));
  say(s, P.ehsan, 60, "What it means for a battery",
    "What does that mean for a battery? Take an illustrative 2,000 milliamp-hour cell at 3.7 volts, which holds " +
    "26,640 joules, and divide by the energy per review. Answering everything on the device gives about 31.5 " +
    "million reviews per charge. Sending everything gives about 89,000. Closing three quarters of the gap gives " +
    "about 517,000: almost six times more than sending everything, for most of the accuracy gain. This counts only " +
    "the energy per review, not idle or sleep power, so it is a comparison between routing choices rather than a " +
    "battery-life prediction.");

  // 21. Limitations and next steps
  s = talk("Part 3: Results, energy and conclusions", "Limits and next steps", P.ehsan, "What's left: measure it on real hardware");
  card(s, 0.6, 1.95, 5.9, 4.7, C.background2, "limitations");
  s.addText("Limitations", T({ x: 0.95, y: 2.2, w: 5.2, h: 0.5, fontSize: 20, bold: true, color: C.accent2 }));
  s.addText(...bulletList([
    "Energy is modelled: datasheet currents, placeholder timings",
    "Pi Zero 2 W latency and int8 model sizes not yet measured",
    "One dataset: long English movie reviews",
    "0.1 points is only 25 of 25,000 test reviews",
  ], { x: 0.95, y: 2.85, w: 5.25, h: 3.6 }));
  const next = [
    ["FaMicrochip", "ESP32-S3 firmware", "tokenise, hash, int8 lookup, route"],
    ["FaServer", "Pi Zero 2 W hub", "int8 ONNX model behind a small HTTP server"],
    ["FaBolt", "INA219 measurements", "real latency and energy per review"],
    ["FaLightbulb", "Better router features", "e.g. disagreement between two device models"],
  ];
  for (let i = 0; i < next.length; i++) {
    const y = 1.95 + i * 1.2;
    await iconCircle(s, 7.0, y + 0.1, 0.7, next[i][0], i < 3 ? C.accent3 : C.accent1);
    s.addText(next[i][1], T({ x: 7.9, y: y + 0.05, w: 4.8, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
    s.addText(next[i][2], T({ x: 7.9, y: y + 0.5, w: 4.8, h: 0.4, fontSize: 15, color: C.text1 }));
  }
  say(s, P.ehsan, 60, "Limits and next steps",
    "We want to be upfront about the limits. The energy is modelled, not measured: datasheet currents with " +
    "placeholder timings, and we have not yet measured the hub's latency or the 8-bit model sizes on the Pi. We used " +
    "one dataset, long English movie reviews. And a 0.1-point difference is only 25 of 25,000 test reviews, so small " +
    "improvements are hard to prove. The next steps are the hardware: ESP32 firmware that tokenises, hashes and " +
    "routes; a Pi hub serving an 8-bit model; and INA219 current measurements for real energy figures. And a better " +
    "router needs new signals, such as disagreement between two small device models.");

  // 22. Conclusion
  s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Part 3: Results, energy and conclusions" });
  s.addText(`CONCLUSION  ·  ${P.ehsan.toUpperCase()}`, { placeholder: "eyebrow", charSpacing: 2 });
  s.addText("Three takeaways", { placeholder: "title" });
  const take = [
    ["1", "Confidence routing is enough", "Learned deferral stayed within 0.14 points of it at every tested send rate, across three hubs."],
    ["2", "Stronger hubs change the game", "They rarely break device answers, which removes deferral's easy win."],
    ["3", "Small sends, big savings", "One review in six closes three quarters of the gap at 6–7× less energy."],
  ];
  for (let i = 0; i < take.length; i++) {
    const x = 0.6 + i * 4.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.2, w: 3.8, h: 2.9, rectRadius: 0.08,
      fill: { color: C.background1, transparency: 88 }, line: { type: "none" }, objectName: `takeaway ${i + 1}` });
    s.addText(take[i][0], T({ x: x + 0.3, y: 2.4, w: 1, h: 0.8, fontFace: "Cambria", fontSize: 40, bold: true,
      color: C.accent5 }));
    s.addText(take[i][1], T({ x: x + 0.3, y: 3.25, w: 3.2, h: 0.75, fontSize: 19, bold: true, color: C.background1,
      valign: "top" }));
    s.addText(take[i][2], T({ x: x + 0.3, y: 4.0, w: 3.2, h: 1.0, fontSize: 15, color: C.background2, valign: "top" }));
  }
  s.addText("Thank you  ·  Questions?", T({ x: 0.6, y: 5.75, w: 12.1, h: 0.8, fontFace: "Cambria", fontSize: 30,
    bold: true, color: C.background1, valign: "middle" }));
  say(s, P.ehsan, 45, "Conclusion",
    "To wrap up, three takeaways. One: confidence routing is enough. Learned deferral stayed within 0.14 points of " +
    "it at every tested send rate, across three hubs. Two: stronger hubs change the game. They rarely break a " +
    "correct device answer, which removes learned deferral's easiest win. Three: small sends, big savings. Sending " +
    "one review in six closes three quarters of the gap at about six times less energy. Thank you. We are happy to " +
    "take your questions.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  writeScripts(path.join(__dirname, "presenter_scripts.md"));
  console.log("wrote", OUT);
}

function writeScripts(file) {
  const total = SCRIPT.reduce((t, x) => t + x.seconds, 0);
  const lines = ["# Presenter scripts", "",
    `Energy-Aware Routing of Sentiment Analysis Between a Microcontroller and a Transformer Hub. ` +
    `${SCRIPT.length} slides, about ${Math.round(total / 60)} minutes. Generated by slides/build_paper_deck.js; ` +
    "the same text is in each slide's speaker notes.", ""];
  let n = 0;
  for (const part of PARTS) {
    const mine = SCRIPT.map((x, i) => ({ ...x, slide: i + 1 })).filter((x) => x.who === part.who);
    const secs = mine.reduce((t, x) => t + x.seconds, 0);
    lines.push(`## ${part.part}: ${part.topic} (${part.who}, about ${Math.round(secs / 60)} min)`, "");
    for (const x of mine) {
      lines.push(`### Slide ${x.slide}: ${x.title} (${Math.floor(x.seconds / 60)}:${String(x.seconds % 60).padStart(2, "0")})`, "", x.text, "");
      n++;
    }
  }
  fs.writeFileSync(file, lines.join("\n"));
}

build().catch((e) => { console.error(e); process.exit(1); });
