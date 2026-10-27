// Builds slides/presenter_scripts.docx: the four presenters' scripts, one part per page, plus the
// running order and Q&A preparation. Reads slides/presenter_scripts.md, which build_paper_deck.js writes
// from the same text as the speaker notes, so rebuild the deck first.
//   NODE_PATH=<dir with docx> node slides/build_scripts_doc.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, Packer, PageBreak, PageNumber, Paragraph,
  ShadingType, Table, TableCell, TableRow, TextRun, WidthType,
} = require("docx");

const MD = fs.readFileSync(path.join(__dirname, "presenter_scripts.md"), "utf8");
const OUT = path.join(__dirname, "presenter_scripts.docx");
const INK = "3A2E31", MUTED = "8A7E80", ROSE = "8C4B57", SAGE = "4A5A50", BLUSH = "F7EFF1", MAUVE = "9C7F89";
const PAGE_W = 11906, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

// ------------------------------------------------------------------ parse the generated markdown
const parts = [];
for (const block of MD.split(/\n(?=## )/).slice(1)) {
  const [head, ...rest] = block.split("\n");
  const m = head.match(/^## (Part \d): (.+) \((.+), about (\d+) min\)$/);
  const slides = rest.join("\n").split(/\n(?=### )/).filter((b) => b.startsWith("### ")).map((b) => {
    const [h, ...body] = b.split("\n");
    const s = h.match(/^### Slide (\d+): (.+) \((\d+:\d\d)\)$/);
    return { n: +s[1], title: s[2], time: s[3], text: body.join(" ").trim() };
  });
  parts.push({ part: m[1], topic: m[2], who: m[3], slides });
}
const seconds = (t) => t.split(":").reduce((a, b) => a * 60 + +b, 0);
const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const total = parts.flatMap((p) => p.slides).reduce((t, s) => t + seconds(s.time), 0);

const QA = [
  ["Why not run a small transformer on the device itself?", "Aditya", "Even DistilBERT has 66 million parameters against 512 KB of on-chip memory; transformers shrunk to microcontroller size lose too much accuracy (Turc et al., 2019)."],
  ["Why IMDb?", "Aditya", "It is the standard benchmark with a known ceiling (about 97%, because 2.9% of test labels are wrong), so our numbers compare with published work."],
  ["How do you know there is no leakage?", "Aditya", "We removed exact copies, near-duplicates, reviews of test movies and every review by a test-set author, and checked that the deferral slice has zero overlap with hub training."],
  ["Why did the v2 device model score lower (92.32%) than v1 (92.69%)?", "Danyson", "Stricter cleaning left 1.55M training reviews instead of 1.94M; removing test-movie reviews alone changed accuracy by only +0.02 points."],
  ["Why only one epoch for the 1M hubs?", "Danyson", "With a million reviews one pass is enough; the best checkpoint is chosen on the 50k val_pool every 2,000 steps."],
  ["How much did it cost, and who paid?", "Danyson", "$2.56 for the two retrained hubs and $17.71 for the large models, itemised from Modal's billing; paid from credits, so $0 was billed."],
  ["Why logistic regression for the router? Would a bigger model help?", "Danyson", "It has to fit on the device next to the 256 KB sentiment model: 128 KB as two int8 tables. The perfect router reaches 97.3% at 5% sent, so the limit is the features, not the classifier."],
  ["Why correct for multiple tests?", "Ehsan", "We ran 15 comparisons; at p < 0.05 one would look significant by chance. Bonferroni sets the bar at 0.05 ÷ 15 = 0.0033."],
  ["Is a one-second hub wait realistic?", "Ehsan", "It is a placeholder. Because the wait dominates, energy is almost proportional to the share sent, so the ratios between routing choices hold; INA219 measurements will fix the absolute numbers."],
  ["Which hub would you deploy?", "Ehsan", "RoBERTa-base is more accurate (96.72% vs 95.83%) but needs about twice the compute per review; the measured Pi latency decides it."],
];

// ------------------------------------------------------------------ helpers
const border = { style: BorderStyle.SINGLE, size: 4, color: "E2D6D9" };
const borders = { top: border, bottom: border, left: border, right: border };

function table(widths, header, rows) {
  const cell = (text, w, head) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 110, right: 110 },
    shading: head ? { fill: MAUVE, type: ShadingType.CLEAR, color: "auto" } : { fill: BLUSH, type: ShadingType.CLEAR, color: "auto" },
    children: [new Paragraph({ children: [new TextRun({ text, bold: head, color: head ? "FFFFFF" : INK, size: 20 })] })],
  });
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, widths[i], false)) }))],
  });
}

const p = (text, opts = {}) => new Paragraph({ spacing: { after: 160 }, ...opts.para,
  children: [new TextRun({ text, size: 22, color: INK, ...opts.run })] });

// ------------------------------------------------------------------ document
const handoff = ["Danyson", "Ehsan", null];
const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Presenter Scripts")] }),
  p("Energy-Aware Routing of Sentiment Analysis Between a Microcontroller and a Transformer Hub",
    { run: { italics: true, size: 24, color: MUTED } }),
  p(`${parts.reduce((n, x) => n + x.slides.length, 0)} slides, about ${clock(total)} minutes. ` +
    "Each part starts on its own page so every presenter can print theirs. The same words are in each slide's " +
    "speaker notes, so presenter view shows them too. Times assume about 130 spoken words a minute."),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Running order")] }),
  table([800, 2000, 1000, 4238, 900, 700].map((w) => Math.round(w * CONTENT_W / 9638)),
    ["Part", "Presenter", "Slides", "Covers", "Time", "Next"],
    parts.map((x, i) => {
      const secs = x.slides.reduce((t, s) => t + seconds(s.time), 0);
      return [x.part.replace("Part ", ""), x.who, `${x.slides[0].n}–${x.slides.at(-1).n}`,
        x.slides.map((s) => s.title).join(", "), clock(secs), handoff[i] || "Q&A"];
    })),
];

parts.forEach((x, i) => {
  const secs = x.slides.reduce((t, s) => t + seconds(s.time), 0);
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(`${x.part}: ${x.who}`)] }));
  children.push(p(`${x.topic} · slides ${x.slides[0].n}–${x.slides.at(-1).n} · about ${clock(secs)} min` +
    (handoff[i] ? ` · hands off to ${handoff[i]}` : " · opens questions"), { run: { color: MUTED, italics: true } }));
  for (const s of x.slides) {
    children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true,
      children: [new TextRun(`Slide ${s.n}: ${s.title}`), new TextRun({ text: `   ${s.time}`, color: MUTED, bold: false })] }));
    // keepLines: a script read aloud should never break across pages mid-paragraph
    children.push(p(s.text, { para: { keepLines: true, spacing: { after: 200, line: 312 } }, run: { size: 24 } }));
  }
});

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Q&A preparation")] }));
children.push(p("Whoever's part a question belongs to answers it; Ehsan moderates and hands each question over."));
children.push(table([3000, 900, 5738].map((w) => Math.round(w * CONTENT_W / 9638)), ["Likely question", "Answers", "Short answer"], QA));

const doc = new Document({
  creator: "Ehsan Abdulkhader, Danyson Antony, Aditya Achar",
  title: "Presenter Scripts",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: INK } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: "Cambria", size: 52, bold: true, color: INK },
        paragraph: { spacing: { after: 80 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Cambria", size: 34, bold: true, color: ROSE }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 25, bold: true, color: SAGE }, paragraph: { spacing: { before: 220, after: 80 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "Presenter scripts · page ", size: 18, color: MUTED }),
      new TextRun({ children: [PageNumber.CURRENT], size: 18, color: MUTED })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
