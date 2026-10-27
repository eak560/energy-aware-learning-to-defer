"""Builds slides/project_update_notes.pdf: plain-language study notes for project_update.pptx.

Every slide gets: what it says, what it means, an analogy, every acronym expanded,
and likely questions with answers. Then an A-Z glossary and a numbers cheat sheet.

    python slides/build_notes_pdf.py   (SLIDE_IMAGES=<folder with slide-01.jpg ...>)
"""

import os
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.lib.fonts import addMapping

HERE = Path(__file__).resolve().parent
OUT = HERE / "project_update_notes.pdf"
IMAGES = Path(os.environ.get("SLIDE_IMAGES", HERE / "notes_images"))

# ------------------------------------------------------------------ fonts and colours
SUP = "/System/Library/Fonts/Supplemental/"
for name, file in [("Arial", "Arial.ttf"), ("Arial-Bold", "Arial Bold.ttf"), ("Arial-Italic", "Arial Italic.ttf"),
                   ("Arial-BoldItalic", "Arial Bold Italic.ttf"), ("Georgia-Bold", "Georgia Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, SUP + file))
addMapping("Arial", 0, 0, "Arial")
addMapping("Arial", 1, 0, "Arial-Bold")
addMapping("Arial", 0, 1, "Arial-Italic")
addMapping("Arial", 1, 1, "Arial-BoldItalic")

MAUVE, ROSE, DARK, INK = HexColor("#9C7F89"), HexColor("#8C4B57"), HexColor("#3A2E31"), HexColor("#2E2A2C")
MUTED, BLUSH, SAGE, SAGE_TEXT = HexColor("#8A7E80"), HexColor("#F7EFF1"), HexColor("#E3EBE5"), HexColor("#4A5A50")
BORDER, WHITE = HexColor("#E2D6D9"), HexColor("#FFFFFF")

S = {
    "title": ParagraphStyle("title", fontName="Georgia-Bold", fontSize=30, leading=36, textColor=DARK),
    "h1": ParagraphStyle("h1", fontName="Georgia-Bold", fontSize=20, leading=25, textColor=DARK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Georgia-Bold", fontSize=14.5, leading=19, textColor=DARK, spaceAfter=3),
    "eyebrow": ParagraphStyle("eyebrow", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=MUTED),
    "lead": ParagraphStyle("lead", fontName="Arial-Italic", fontSize=10.5, leading=14.5, textColor=ROSE),
    "body": ParagraphStyle("body", fontName="Arial", fontSize=10.2, leading=14.6, textColor=INK, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="Arial", fontSize=10.2, leading=14.4, textColor=INK, leftIndent=12,
                             bulletIndent=2, spaceAfter=2.5, bulletFontName="Arial"),
    "boxtitle": ParagraphStyle("boxtitle", fontName="Arial-Bold", fontSize=9.5, leading=12, textColor=ROSE, spaceAfter=3),
    "box": ParagraphStyle("box", fontName="Arial", fontSize=9.8, leading=13.8, textColor=INK, spaceAfter=3,
                          bulletFontName="Arial"),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8.6, leading=11.5, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.8, leading=11.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Arial-Bold", fontSize=8.8, leading=11.6, textColor=DARK),
    "cellh": ParagraphStyle("cellh", fontName="Arial-Bold", fontSize=8.8, leading=11.6, textColor=WHITE),
}
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ------------------------------------------------------------------ building blocks
def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def box(title, flowables, bg=BLUSH, title_color=ROSE, border=None):
    title_style = ParagraphStyle("bt", parent=S["boxtitle"], textColor=title_color)
    cell = [Paragraph(title, title_style)] + flowables
    t = Table([[cell]], colWidths=[CONTENT_W])
    style = [("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10),
             ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
    if border:
        style.append(("BOX", (0, 0), (-1, -1), 0.8, border))
    t.setStyle(TableStyle(style))
    return t


def terms_box(terms):
    """terms: list of (term, expansion_or_None, meaning)."""
    lines = []
    for term, expansion, meaning in terms:
        exp = f" = <i>{expansion}</i>" if expansion else ""
        lines.append(Paragraph(f"<b>{term}</b>{exp}: {meaning}", S["box"], bulletText="•"))
    return box("ACRONYMS AND TERMS ON THIS SLIDE", lines, bg=SAGE, title_color=SAGE_TEXT)


def qa_box(pairs):
    flow = []
    for q, a in pairs:
        flow.append(Paragraph(f"<b>Q: {q}</b>", S["box"]))
        flow.append(Paragraph(f"A: {a}", S["box"]))
    return box("IF SOMEONE ASKS…", flow, bg=WHITE, title_color=DARK, border=BORDER)


def slide_header(n, title, one_liner):
    img_path = IMAGES / ("fixed-11.jpg" if n == 11 and (IMAGES / "fixed-11.jpg").exists() else f"slide-{n:02d}.jpg")
    img = Image(str(img_path), width=62 * mm, height=62 * mm * 9 / 16) if img_path.exists() else Spacer(62 * mm, 1)
    text = [P(f"SLIDE {n}", "eyebrow"), P(title, "h2"), P(one_liner, "lead")]
    t = Table([[img, text]], colWidths=[62 * mm, CONTENT_W - 62 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (0, 0), 0),
                           ("BOTTOMPADDING", (0, 0), (0, 0), 0), ("LEFTPADDING", (1, 0), (1, 0), 12),
                           ("BOX", (0, 0), (0, 0), 0.6, BORDER)]))
    return t


def slide_section(n, title, one_liner, says, means, analogy, terms, qa):
    out = [CondPageBreak(90 * mm), slide_header(n, title, one_liner), Spacer(1, 7)]
    out += [P("<b>What the slide says</b>", "body")] + bullets(says) + [Spacer(1, 4)]
    out += [P("<b>What it means</b>", "body")] + [P(m) for m in means] + [Spacer(1, 3)]
    out += [box("ANALOGY: EXPLAIN IT LIKE THIS", [P(a, "box") for a in analogy]), Spacer(1, 6)]
    if terms:
        out += [terms_box(terms), Spacer(1, 6)]
    out += [qa_box(qa), Spacer(1, 14)]
    return out


def table(rows, widths, header_bg=MAUVE):
    data = [[Paragraph(c, S["cellh"]) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(r[0], S["cellb"])] + [Paragraph(c, S["cell"]) for c in r[1:]])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), header_bg), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BLUSH]),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER), ("LEFTPADDING", (0, 0), (-1, -1), 5),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def on_page(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 10 * mm, "Energy-Aware Hybrid Sentiment Analysis · Notes for the project update deck")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ------------------------------------------------------------------ content
def cover():
    return [
        Spacer(1, 40 * mm), P("NOTES FOR THE PROJECT UPDATE DECK", "eyebrow"), Spacer(1, 6),
        P("Energy-Aware Hybrid Sentiment Analysis", "title"), Spacer(1, 8),
        P("A plain-language guide to every slide: what it says, what it means, an everyday analogy for "
          "explaining it, every acronym spelled out, and the questions you are likely to be asked.", "lead"),
        Spacer(1, 14),
        P("Ehsan Abdulkhader 24BCT0089 · Danyson Antony 24BAI0196 · Aditya Achar 24BCI0250", "small"),
        Spacer(1, 28 * mm),
        box("HOW TO USE THESE NOTES", bullets([
            "<b>Part 1</b> tells the whole story in one page with a single analogy you can reuse all the way through.",
            "<b>Part 2</b> goes slide by slide (17 slides). Each slide has five parts: what it says, what it means, "
            "an analogy, the acronyms and terms on it, and likely questions with answers.",
            "<b>Part 3</b> is an A to Z glossary: every acronym and technical word, what it stands for, what it means "
            "and an analogy.",
            "<b>Part 4</b> is a cheat sheet of every number in the deck.",
            "<b>Part 5</b> lists the hardest questions you could be asked, with honest answers.",
        ], "box")),
        PageBreak(),
    ]


def part1():
    return [
        P("PART 1", "eyebrow"), P("The whole story on one page", "h1"),
        P("<b>The task.</b> Sentiment analysis means reading a piece of text, such as a movie review, and deciding "
          "whether it is positive or negative. We use the standard IMDb (Internet Movie Database) benchmark: "
          "25,000 reviews to learn from and 25,000 separate reviews to be graded on."),
        P("<b>The idea.</b> Instead of one model, we built a two-tier \"hybrid\". A tiny model runs on a cheap, "
          "battery-powered chip and answers most reviews itself. Only the reviews it is unsure about are sent over "
          "Wi-Fi to a bigger, smarter model (a \"transformer\") on a small nearby computer, the \"hub\". A decision-maker "
          "in between, the \"router\", decides which reviews are worth sending, because every send costs battery."),
        P("<b>Why it matters.</b> Devices that run on batteries (robots, handheld messengers, watches, toys) cannot run "
          "big models all the time, and sending everything over the radio drains the battery. Our system gets "
          "nearly the big model's accuracy while sending only about 5 to 10% of reviews."),
        P("<b>The record.</b> Separately, we trained three large transformer models on about one million extra, "
          "carefully cleaned movie reviews and combined them. That combination scores 97.40% on the IMDb test set, "
          "above the best published result we know of (97.1%). Because we used extra training data, this is reported "
          "as an \"extra-data\" result."),
        P("<b>The honesty work.</b> We found that 91% of the official test reviews were sitting inside the public "
          "download we used for extra data. We removed every copy, every review of a test-set movie and every review "
          "by a test-set author, then graded the final model on the test set exactly once."),
        Spacer(1, 4),
        box("THE ONE ANALOGY THAT EXPLAINS EVERYTHING: A HOSPITAL", bullets([
            "<b>The tiny on-device model is the triage nurse</b> at the front desk: quick, cheap, handles most patients.",
            "<b>The transformer hub is the specialist doctor</b>: slower and more expensive, but better with hard cases.",
            "<b>The router is the referral decision.</b> \"Confidence routing\" means the nurse refers whenever she is "
            "unsure. \"Learning to defer\" means the nurse learns which cases the specialist actually gets right.",
            "<b>Energy-aware</b> means every referral costs an ambulance ride (battery), so the nurse only refers "
            "when it is worth the trip.",
            "<b>Data leakage</b> is like a student who studied from a book that secretly contained the final exam. "
            "We tore those pages out before grading.",
        ], "box")),
        PageBreak(),
    ]


SLIDES = [
    dict(n=1, title="Energy-Aware Hybrid Sentiment Analysis",
         one="The title slide: what the project is called and who built it.",
         says=["Project name: <b>Energy-Aware Hybrid Sentiment Analysis</b>.",
               "Subtitle: Sentiment Analysis of Text Reviews Using Machine Learning, \"from a $5 chip to a "
               "record-setting ensemble\".", "The three team members."],
         means=["<b>Sentiment analysis</b> is deciding whether text is positive or negative. <b>Hybrid</b> means two "
                "models work together: a small fast one and a large accurate one. <b>Energy-aware</b> means the system "
                "considers battery cost before using the large one.",
                "The subtitle names the two achievements: a model small enough for a $5 chip, and an "
                "<b>ensemble</b> (a team of models combined) that beats the published IMDb record."],
         analogy=["Think of a clinic with a triage nurse and a specialist. The nurse handles everyday cases; the "
                  "specialist is called only when needed, and calling them costs something. That is the whole project."],
         terms=[("Machine learning", None, "teaching a computer from examples instead of writing rules by hand"),
                ("Ensemble", None, "several models whose answers are combined into one, like a panel of judges")],
         qa=[("What is sentiment analysis used for?",
              "Reading product reviews, customer feedback and social media at scale, and helping devices such as "
              "robots react to how a person feels.")]),
    dict(n=2, title="Three headline results",
         one="The three numbers to remember: 97.40%, 14–19× and 256 KB.",
         says=["<b>97.40%</b> IMDb test accuracy, above the best published result (97.1%), using about 1 million "
               "extra leak-free reviews (the \"extra-data setting\").",
               "<b>14–19×</b> less device energy to match the transformer's accuracy, based on ESP32-S3 datasheet "
               "currents; the timings still need measuring.",
               "<b>256 KB</b> on-chip model reaching 92.3% test accuracy, small enough for an ESP32-S3 with 512 KB of RAM.",
               "Footer: every choice was made on a 50,000-review validation set; the test set was scored once."],
         means=["<b>97.40%</b> means that out of 25,000 test reviews the model labels about 24,350 correctly. The best "
                "published score we found is 97.1% (a model called ERNIE-Doc). Because we used extra training data, "
                "we compare ourselves fairly only within that category.",
                "<b>14–19×</b>: if the device sent every review to the big model, it would spend 14 to 19 times more "
                "battery per review than our system does, for the same accuracy.",
                "<b>256 KB</b> is the size of the tiny model, smaller than a single phone photo (about 3 MB)."],
         analogy=["97.40% is like scoring 97.4 out of 100 on an exam where the best score anyone has published is "
                  "97.1, while being clear that you also used extra practice books.",
                  "14–19× less energy is like walking to most errands and taking a taxi only for the far ones.",
                  "A 256 KB model is a whole \"reader\" that fits in less space than one holiday photo."],
         terms=[("IMDb", "Internet Movie Database", "the movie website whose reviews form the standard test"),
                ("KB", "kilobyte", "about a thousand bytes (1,024); 256 KB is a quarter of a megabyte"),
                ("RAM", "Random Access Memory", "the chip's working memory, where a program must fit while running"),
                ("ESP32-S3", None, "a cheap microcontroller (tiny computer on a chip) made by Espressif Systems; "
                 "\"32\" refers to its 32-bit processor family, \"S3\" is the model series"),
                ("Datasheet", None, "the manufacturer's official specification document for a chip"),
                ("Validation set", None, "practice data used to make choices; the test set is kept for the final grade")],
         qa=[("Is 97.40% definitely better than 97.1%?",
              "On this test set, yes with high confidence: our 95% confidence interval is 97.21% to 97.58%, entirely "
              "above 97.1%. But it is an extra-data result, so it belongs in that category of the leaderboard."),
             ("Why say 14–19× instead of one number?",
              "The saving depends on how long the device waits for the hub's reply, which we have not measured yet. "
              "Across waits from 0.1 to 2 seconds the saving stays between 14× and 19×.")]),
    dict(n=3, title="From one model to a two-tier hybrid",
         one="What we planned at the last review, compared with what we actually built.",
         says=["<b>Last review's plan:</b> TF-IDF + VADER + logistic regression; one model on a CPU; 25,000 IMDb "
               "training reviews; target about 90% accuracy.",
               "<b>Now:</b> tiny on-device model + transformer hub; learning to defer + energy-aware routing; 4.1 "
               "million cleaned reviews audited for test leakage; large transformers trained on cloud GPUs; 97.40%."],
         means=["The old plan was a single classic model with one extra feature from VADER, a ready-made sentiment "
                "word list. The new system has two models, a router between them, millions more training examples, "
                "and a separate record attempt with large models trained on rented cloud graphics cards.",
                "<b>TF-IDF</b> turns a review into numbers by counting words, giving more weight to words that are "
                "frequent in this review but rare overall. <b>Logistic regression</b> then adds up a learned weight for "
                "each word and turns the total into a probability of \"positive\"."],
         analogy=["TF-IDF is a highlighter that marks the words that make this review distinctive (\"superb\", "
                  "\"waste\") and ignores common filler (\"the\", \"movie\").",
                  "Logistic regression is a balance scale: positive words add weight to one side, negative words to "
                  "the other, and the scale's tilt is the answer.",
                  "VADER is a dictionary that lists each word's mood score in advance.",
                  "The change is like going from one family doctor to a clinic with a triage nurse and a specialist."],
         terms=[("TF-IDF", "Term Frequency–Inverse Document Frequency",
                 "word counts, weighted up for words that are rare across all reviews"),
                ("VADER", "Valence Aware Dictionary and sEntiment Reasoner",
                 "a rule-based sentiment tool built on a hand-scored word list (\"valence\" means emotional positivity)"),
                ("Logistic regression", None, "a simple, interpretable model that weighs features and outputs a probability"),
                ("CPU", "Central Processing Unit", "the computer's main general-purpose processor"),
                ("GPU", "Graphics Processing Unit", "a processor with thousands of small cores, ideal for AI training"),
                ("Transformer", None, "a modern neural-network design that reads all words together and pays "
                 "\"attention\" to how they relate"),
                ("Leakage", None, "test answers accidentally ending up in the training data")],
         qa=[("Why did you drop VADER?",
              "It would have added one extra signal to one model, for a small expected gain. The hybrid design "
              "offered much larger improvements in accuracy and an energy story."),
             ("Is the old TF-IDF model still used?",
              "Its descendant is: the tiny on-device model is the same idea (word patterns + weights), made small enough "
              "for a chip and trained on far more data.")]),
    dict(n=4, title="How the hybrid works",
         one="The pipeline: every review hits the tiny model; only the worthwhile ones go to the hub.",
         says=["Review (typed, or speech converted to text) → tiny model on the device (256 KB, milliseconds) → "
               "\"Worth sending?\" router (gain versus battery cost) → transformer hub (answers the hard 5–10%).",
               "If not worth sending, the device answers itself.",
               "Router contributions: learning to defer, and energy-aware routing.",
               "Device: ESP32-S3 (about $5, 512 KB RAM). Hub: Raspberry Pi Zero 2 W ($15, 512 MB RAM). Same local "
               "network, so no internet is needed."],
         means=["Most reviews are easy (\"Brilliant, loved it\"), so the tiny model answers them instantly and for "
                "almost no energy. Hard reviews (sarcasm, mixed opinions) are sent to the hub, which runs a "
                "transformer and is more accurate.",
                "The router is the new part. <b>Learning to defer</b> trains it to predict whether the hub would "
                "actually fix the tiny model's answer. <b>Energy-aware routing</b> sends a review only when the expected "
                "gain is worth the battery the radio uses.",
                "Because the device and hub talk over a local network, the system works with no internet, and reviews "
                "never leave the building."],
         analogy=["A local post office handles ordinary letters itself and forwards only unusual parcels to the "
                  "central sorting office. Forwarding costs postage (battery), so the clerk forwards only when it "
                  "matters.",
                  "Or: a student answers the questions they are sure about and asks the teacher only about the tricky ones."],
         terms=[("ESP32-S3", None, "Espressif Systems' low-cost microcontroller; 512 KB RAM, built-in Wi-Fi"),
                ("Raspberry Pi Zero 2 W", None, "a $15 credit-card-sized Linux computer; the \"W\" stands for "
                 "wireless (built-in Wi-Fi and Bluetooth)"),
                ("RAM", "Random Access Memory", "working memory: the device has 512 KB, the hub 512 MB (1,000× more)"),
                ("MB", "megabyte", "about a million bytes (1,024 KB)"),
                ("Wi-Fi", None, "a brand name for wireless networking, not an acronym; \"Wireless Fidelity\" is a "
                 "popular myth"),
                ("Speech-to-text", None, "software that turns spoken words into written text, also called STT")],
         qa=[("Why not run the transformer on the device directly?",
              "Even the small transformer we used (DistilBERT) has 66 million parameters, about 66 MB when "
              "compressed. The ESP32-S3 has 512 KB of RAM, over 100 times too small."),
             ("What happens if the Wi-Fi is down?",
              "The device still answers every review with the tiny model (about 92% accurate); it simply cannot "
              "send the hard ones for a second opinion.")]),
    dict(n=5, title="Robots: a leading battery-powered use case",
         one="Why the energy angle is real: robots spend much of their battery on computing.",
         says=["Computing drains robot batteries, not just driving: measured robots use 30–90 W, and motors take "
               "only 16.6–54.6% of that (Liu, Shi &amp; Shin 2025).",
               "Big models on board cost hours of battery: larger onboard GPUs \"drain robot batteries several hours "
               "faster\"; offloading helps but adds delay and network load (Pohland et al. 2026).",
               "Robots care about sentiment: reading how a person feels is an established goal in human-robot "
               "interaction (Spezialetti, Placidi &amp; Rossi 2020).",
               "Note: robots hear speech, so speech-to-text runs first; on a robot, the \"device\" tier is its own computer."],
         means=["People assume a robot's battery goes on wheels and arms. Measurements show the motors use only "
                "between about a sixth and a half of the power; the rest goes to computing and sensors. So making the "
                "thinking cheaper genuinely extends battery life.",
                "Robots that work with people (in care homes, hospitals, homes) benefit from knowing if someone is "
                "frustrated or happy, which is sentiment analysis.",
                "Robots are one of the biggest use cases, but not the only one; the next slide lists others."],
         analogy=["A robot's battery is like your phone's: the screen and processor drain it as much as anything "
                  "else. Running a huge model on board is like gaming on your phone all day.",
                  "Offloading is like phoning a friend to do hard maths for you: it saves your effort, but the call "
                  "takes time and costs credit."],
         terms=[("W", "watt", "a unit of power, energy used per second; a phone charger is about 20 W"),
                ("GPU", "Graphics Processing Unit", "the chip that runs large AI models; power-hungry"),
                ("Offloading", None, "sending work to another computer instead of doing it yourself"),
                ("Human-robot interaction", None, "the research field on how robots and people work together "
                 "(often shortened to HRI)")],
         qa=[("Why lead with robots?",
              "They run on batteries, computing is a large share of their power, and they interact with people, so "
              "sentiment matters. But we deliberately present them as one use case among several."),
             ("Robots hear speech, not text. Does the system still apply?",
              "Yes. A speech-to-text step turns speech into text first, and the router works on that text.")]),
    dict(n=6, title="Use cases, ranked by fit",
         one="Where energy-aware sentiment analysis makes sense, from strongest to weakest.",
         says=["Social, assistive and eldercare robots: strongest story.",
               "Off-grid messengers such as the LILYGO T-Deck: best hardware match (text is typed straight into an ESP32-S3).",
               "Smartwatch with the phone as hub: believable. Kids' smart toys and battery or solar feedback kiosks: niche.",
               "Drones and smart speakers: not a fit (no text, or plugged into the wall)."],
         means=["Each row is judged on three things: does it run on a battery, how does text arrive, and could it use "
                "the same cheap chip. The best fits score well on all three.",
                "The T-Deck is a handheld device with a keyboard, built on the same ESP32-S3 chip, that sends text "
                "messages with no phone network using a long-range radio. That makes it the closest real-world match "
                "to our setup."],
         analogy=["A mesh messenger is like passing notes from person to person across a stadium until it reaches "
                  "the right seat: no phone tower needed.",
                  "LoRa is like a walkie-talkie for short text messages that can reach several kilometres."],
         terms=[("LILYGO T-Deck", None, "a handheld ESP32-S3 device with a keyboard, screen and LoRa radio"),
                ("LoRa", "Long Range", "a low-power radio technology that sends small messages over long distances"),
                ("Meshtastic", None, "free, open-source software that turns LoRa devices into an off-grid text-messaging mesh"),
                ("Off-grid", None, "working without mobile networks or the internet"),
                ("Hub", None, "the nearby, more powerful device that answers the hard cases (here, a phone or a Raspberry Pi)")],
         qa=[("Which one would you actually build first?",
              "The T-Deck: it uses exactly our chip, people type real text into it, and every radio message costs battery.")]),
    dict(n=7, title="Millions of labelled reviews",
         one="Where the extra training data came from, and how reviews were labelled.",
         says=["IMDb Review Dataset on Kaggle (free, public domain): 5,571,499 reviews, giving 4.1 million clean reviews.",
               "Amazon Reviews 2023, Movies &amp; TV on Hugging Face: 17.3 million reviews, giving 12.0 million clean reviews. "
               "Tested, but it did not help IMDb accuracy, so it was left out.",
               "Labels: IMDb 4 out of 10 or lower = negative, 7 or higher = positive. Amazon 1–2 stars = negative, "
               "4–5 stars = positive. Middle ratings dropped; Amazon review titles dropped because they often state the rating."],
         means=["A <b>labelled</b> review is one where we know the right answer. Here the reviewer's own star rating "
                "gives the label, so millions of labels come for free.",
                "We drop middle ratings (5–6 out of 10, or 3 stars) because those reviews are genuinely mixed and would "
                "confuse the model. Amazon titles like \"Five Stars\" literally contain the answer, so we threw them away.",
                "Amazon reviews are short and about products, so they did not teach the model much about long movie "
                "reviews; we measured this and removed them."],
         analogy=["Labelled reviews are flashcards with the answer on the back. Dropping middle ratings removes the "
                  "flashcards where even the author was unsure.",
                  "Keeping Amazon titles would be like flashcards with the answer printed on the front.",
                  "Training on Amazon to improve on IMDb is like practising essay writing by reading text messages: "
                  "related, but the wrong style."],
         terms=[("Kaggle", None, "a popular website for sharing datasets and data-science competitions"),
                ("Hugging Face", None, "a website that hosts AI models and datasets; our standard IMDb copy also comes from there"),
                ("CC0", "Creative Commons Zero", "a licence that puts data in the public domain, free for any use"),
                ("Dataset", None, "an organised collection of examples, here reviews with ratings"),
                ("Clean", None, "after removing duplicates, unrated reviews and anything overlapping the test set")],
         qa=[("Are star ratings reliable labels?",
              "Mostly. We checked: on reviews that appear in both the Kaggle data and the official IMDb set, our "
              "rating rule agreed with the official label 99.92% of the time."),
             ("Why not use all 12 million Amazon reviews anyway?",
              "Adding them did not improve accuracy on movie reviews (it was slightly worse on test), and simpler is better.")]),
    dict(n=8, title="91% of the test set was hiding in the download",
         one="The leakage audit: the public data contained most of the exam, and we removed it.",
         says=["Chart: 5,571,499 downloaded → 4,186,661 with a usable rating → 4,099,728 after removing copies and "
               "duplicates → 3,336,925 sharing no movies or authors with the test set.",
               "23,636 copies of official test reviews were in the public download and were removed.",
               "Round 1: exact matches plus matches on the first or last 200 characters. Round 2: reviews of test-set "
               "movies (163,409), by test-review authors (635,853), and near-duplicates (443)."],
         means=["The extra data was scraped from the same website as the official test set, so the test reviews were "
                "inside it, with their star ratings. A model trained on that would have \"seen the answers\" and "
                "scored unrealistically high.",
                "We removed exact copies and edited copies, then went further: every review of a movie that appears "
                "in the test set, and every review written by someone who also wrote a test review. That is stricter "
                "than many published papers."],
         analogy=["Imagine studying from a revision book that secretly contains the final exam with the answers. "
                  "We tore out those pages, then also every page about the same topics (movies) and every page "
                  "written by the same examiner (authors).",
                  "A near-duplicate is a photocopy with a few words changed: still the exam, just disguised."],
         terms=[("Leakage", None, "test information sneaking into training data, which makes scores look better than they really are"),
                ("De-duplication", None, "finding and removing copies, exact or nearly exact"),
                ("Scrape", None, "a dataset collected automatically from a website"),
                ("Movie-disjoint / author-disjoint", None, "no movie, or no author, appears on both the training and test sides"),
                ("Near-duplicate", None, "here: a review sharing 30% or more of its 8-word phrases with a test review")],
         qa=[("How do you know you removed all the leakage?",
              "We used several independent checks (exact, partial, near-duplicate, movie and author), an AI "
              "reviewer agent audited the pipeline, and on a test set with duplicates removed the score is unchanged (97.40%)."),
             ("Doesn't removing so much data hurt?",
              "We still had 3.3 million clean reviews, far more than we could even use, so it costs almost nothing.")]),
    dict(n=9, title="How we kept the evaluation honest",
         one="Five rules that make the 97.40% believable.",
         says=["1. Lock the test set: the official 25,000 test reviews are never used for training or choices.",
               "2. Clean the extra data: no copies, no shared movies or authors.",
               "3. Choose on val_pool: 50,000 reviews from held-out movies, length-matched to the test set.",
               "4. Score the test once: the final ensemble is evaluated a single time.",
               "5. Report uncertainty: 95% confidence interval, McNemar tests, de-duplicated test score.",
               "Footer: an adversarial reviewer agent audited the pipeline and found problems that were fixed."],
         means=["If you try many options and keep whichever scores best on the test set, you have quietly tuned to the "
                "test, and the score is inflated. So every decision (which model version, how to combine them) was made "
                "on a separate practice set, val_pool, and the test set was used exactly once.",
                "val_pool comes from movies no model trained on, and its review lengths match the test set, so it "
                "behaves like the test set without being it.",
                "An <b>adversarial reviewer agent</b> is an AI assistant we asked to attack our own method. It caught "
                "a misquoted record, a number we had picked using the test set, and missed leaks."],
         analogy=["The test set is the sealed final exam. val_pool is a set of mock exams: you can sit them as often as "
                  "you like to decide how to study, but the final is opened once.",
                  "Reporting a confidence interval is like an opinion poll saying \"52%, give or take 2%\"."],
         terms=[("val_pool", "validation pool", "our 50,000-review practice set built from held-out movies"),
                ("Confidence interval", None, "a range that very likely contains the true accuracy (often shortened to CI)"),
                ("95%", None, "the confidence level: ranges built this way contain the true value 95 times out of 100"),
                ("McNemar test", None, "a statistical test comparing two models on the same questions, counting only "
                 "the questions where they disagree (named after Quinn McNemar)"),
                ("Adversarial review", None, "deliberately trying to break your own argument before others do")],
         qa=[("Why not just use the official 5,000-review validation split?",
              "It is too small to separate models that differ by 0.1–0.3 points, and it shares movies with the extra data, "
              "so it is optimistic."),
             ("What did the reviewer agent find?",
              "Our quoted records were out of date (the real best is 97.1%), one cascade number had been chosen using "
              "the test set, and some leaks were missed. All were fixed.")]),
    dict(n=10, title="For the tiny model, more data beats more size",
         one="The on-device model gets better mainly by seeing more examples, not by being bigger.",
         says=["Chart: validation accuracy of the 256 KB model rises from 90.2% (20,000 reviews) to 91.1% (100k), "
               "91.8% (300k), 92.3% (1 million) and 92.8% (1.94 million).",
               "Size on the chip (20,000 reviews): 16 KB 86.6%, 64 KB 89.3%, 256 KB 90.3%, 1 MB 90.6%.",
               "Cleaned data, final: 256 KB gives 92.32% test, 1 MB gives 92.80% test.",
               "Footer: hashed word pairs, Naive Bayes weighting, int8 storage, no vocabulary on the device."],
         means=["Going from 256 KB to 1 MB adds only about 0.3 points, while going from 20,000 to 1.94 million "
                "reviews adds about 2.6 points. So the best way to improve the tiny model is more training data, which "
                "costs nothing on the device.",
                "<b>How it fits in 256 KB:</b> instead of storing a dictionary of words, each word and each pair of "
                "words (\"not good\") is turned into a number between 0 and 262,143 by a fixed formula (hashing). The "
                "chip stores one small weight per number, each as an 8-bit integer.",
                "The cleaned-data score (92.32%) is a little lower than an earlier 92.69% because the earlier "
                "training data still contained reviews by test-set authors, which flattered the score slightly."],
         analogy=["Hashing is a cloakroom: each phrase gets a numbered hook, and you never need a list of names. Two "
                  "phrases occasionally share a hook, which costs a tiny bit of accuracy.",
                  "int8 storage is like rounding prices to whole rupees so your notebook fits in a pocket.",
                  "More data versus more size: a small notebook filled with a million experiences beats a big notebook "
                  "with only twenty thousand."],
         terms=[("KB / MB", "kilobyte / megabyte", "units of storage; 1 MB = 1,024 KB"),
                ("n-gram", None, "a run of n words; \"word pairs\" are 2-grams, like \"not good\""),
                ("Hashing", None, "turning any text into a number with a fixed formula, so no word list is stored"),
                ("Naive Bayes weighting", None, "scoring each feature by how much more often it appears in positive "
                 "than negative reviews; \"naive\" because it treats words as independent"),
                ("int8", "8-bit integer", "a whole number from −128 to 127, stored in one byte (we use −127 to 127)"),
                ("Quantization", None, "storing numbers with less precision (here int8) to save space")],
         qa=[("Why not use a 1 MB model if it is more accurate?",
              "It also fits on the chip's flash storage, and we report both. 256 KB leaves room for the router and "
              "the rest of the device software."),
             ("Does int8 rounding hurt accuracy?",
              "Barely: in our tests the difference was about 0.1 points or less.")]),
    dict(n=11, title="Transformer accuracy from a fraction of the reviews",
         one="The cascade (tiny model first, hub for hard cases) matches or beats the hub while sending few reviews.",
         says=["Chart: accuracy (vertical) against the percentage of reviews sent to the hub (horizontal), for "
               "learned deferral, confidence routing, a perfect router (upper bound) and the hub alone (93.51%).",
               "94.05% when sending 10.7% of reviews, with the threshold chosen on validation.",
               "About 5% sent is enough to match the hub.",
               "Learned deferral vs confidence routing: within ±0.1 points, so no real gain yet.",
               "Footer: first-round data, 256 KB chip model (92.69%) and DistilBERT hub (93.51%)."],
         means=["Sending only the reviews the tiny model is least sure about already reaches the hub's accuracy at "
                "about 5% sent. At about 10% sent the combination beats both models alone, because they make different "
                "mistakes.",
                "The <b>perfect router</b> is an impossible \"cheat\" that knows which reviews the hub would fix. It "
                "shows the ceiling: about 96.6% sending only about 4%. The gap between it and our routers is the room "
                "for improvement.",
                "<b>Learning to defer</b> did not beat the simple rule. Our explanation: the hub was trained on only "
                "20,000 reviews, so it fixes the chip (4.1% of reviews) almost as often as it breaks it (3.9%), "
                "leaving little pattern to learn. This is an honest negative result.",
                "\"Thresholds set by send rate (no labels used)\" means each point on the curve sends the top x% most "
                "uncertain reviews, chosen without looking at the right answers."],
         analogy=["A teacher who double-checks only the answers a student marked as \"not sure\" catches most mistakes "
                  "while checking very few papers.",
                  "The perfect router is a teacher who already knows which answers are wrong: useful as a yardstick, "
                  "impossible in real life."],
         terms=[("Cascade", None, "models arranged in sequence: cheap first, expensive only when needed"),
                ("Confidence routing", None, "send a review when the tiny model's confidence is below a threshold"),
                ("Learning to defer", None, "a trained router that predicts whether sending will actually help"),
                ("Threshold", None, "the cut-off confidence below which a review is sent"),
                ("DistilBERT", "distilled BERT", "a smaller, faster version of BERT (66 million parameters) trained to "
                 "imitate it; BERT = Bidirectional Encoder Representations from Transformers"),
                ("Perfect router / oracle", None, "a hypothetical router that knows the true answers; an upper bound only")],
         qa=[("How can the combination beat the hub alone?",
              "On the reviews the tiny model is confident about, it is often right where the hub is wrong. Keeping its "
              "confident answers and sending only the doubtful ones gets the best of both."),
             ("So was learning to defer a failure?",
              "It is a negative result for now. With a stronger hub trained on more data, the hub's fixes should be "
              "more predictable; that rerun is in the next steps.")]),
    dict(n=12, title="19× less device energy at the transformer's accuracy",
         one="The energy saving, and exactly what it is based on.",
         says=["Bars: sending every review costs 300.6 mJ per review; the cascade at hub accuracy (5% sent) costs 15.8 mJ; "
               "the device alone costs 0.8 mJ.",
               "From the ESP32-S3 datasheet: Wi-Fi transmit 283 mA, receive 88 mA, processor 51.2 mA, at 3.3 V.",
               "Placeholders, to be measured: 5 ms on the chip, 10 ms to send, 1 s waiting for the hub.",
               "The 14–19× saving holds for hub waits from 0.1 to 2 seconds."],
         means=["Energy = voltage × current × time. The radio draws far more current than the processor (283 mA "
                "versus 51.2 mA), and the device also has to keep listening while it waits for the hub's reply. So "
                "every send is expensive, and sending only 5% of reviews saves most of that energy.",
                "300.6 ÷ 15.8 ≈ 19. The currents are official figures; the timings are our estimates until we measure "
                "them on a real board. That is why the slide labels them as placeholders."],
         analogy=["Think of millijoules as coins. Answering on the chip costs less than one coin; sending to the hub "
                  "costs hundreds, mostly spent waiting \"on hold\" for the reply.",
                  "Using the Wi-Fi radio is like making a phone call; thinking on the chip is like thinking quietly to yourself."],
         terms=[("mJ", "millijoule", "a thousandth of a joule, the unit of energy; a typical phone battery holds about 55,000 joules"),
                ("mA", "milliampere", "a thousandth of an ampere, the unit of electric current"),
                ("V", "volt", "the unit of electrical \"pressure\"; the chip runs at 3.3 V"),
                ("ms", "millisecond", "a thousandth of a second"),
                ("Datasheet", None, "the manufacturer's official specification, where the current figures come from"),
                ("Placeholder", None, "a stand-in value used until the real one is measured")],
         qa=[("Isn't an estimate based on guesses unreliable?",
              "The currents are measured by the manufacturer. Only the timings are estimated, and the conclusion "
              "(14–19× saving) holds across a wide range of waiting times. We will confirm it with real measurements."),
             ("How will you measure it?",
              "With an INA219 current sensor between the battery and the ESP32-S3, logging current while it runs.")]),
    dict(n=13, title="97.40%: above the best published IMDb result",
         one="Our models compared with the published records.",
         says=["Published: LlamBERT 96.68% (also extra data), XLNet 96.80%, ERNIE-Doc 97.10% (best published).",
               "Ours: RoBERTa-large on official data only 96.54%; with 1 million extra reviews RoBERTa-large 97.21%, "
               "ELECTRA-large 97.22%, DeBERTa-v3-large 97.33%; our ensemble 97.40%.",
               "95% confidence interval 97.21–97.58%. De-duplicated test: 97.40%. Beats our best single model (p = 0.046).",
               "Footer: the ensemble combines ELECTRA, DeBERTa and the 1 MB n-gram model, by stacking."],
         means=["Our <b>RoBERTa-large trained on official data only</b> scores exactly the published 96.54%. That "
                "proves our setup matches everyone else's, so the gains afterwards come from the extra data, not a quirk.",
                "Adding one million cleaned reviews lifts each large model by about 0.7 points. Combining two of them with "
                "the tiny n-gram model adds a little more, reaching 97.40%.",
                "<b>p = 0.046</b> means: if the ensemble and the best single model were really equally good, a gap this "
                "large would happen by chance only about 4.6% of the time. Below 5% is the usual bar for \"significant\".",
                "<b>Stacking</b> means a small extra model learns how much to trust each member, using the practice set."],
         analogy=["The ensemble is a panel of judges. Stacking is a head judge who has learned from past contests "
                  "which judge to trust more.",
                  "Matching the published 96.54% first is like calibrating your scales against a known weight before "
                  "weighing anything else."],
         terms=[("BERT", "Bidirectional Encoder Representations from Transformers",
                 "Google's 2018 language model that reads text in both directions; the family most of these models come from"),
                ("RoBERTa", "Robustly Optimized BERT Pretraining Approach", "Meta's improved retraining of BERT"),
                ("ELECTRA", "Efficiently Learning an Encoder that Classifies Token Replacements Accurately",
                 "Stanford and Google's model, trained to spot which words have been swapped"),
                ("DeBERTa-v3", "Decoding-enhanced BERT with disentangled Attention, version 3",
                 "Microsoft's model that treats word meaning and word position separately"),
                ("XLNet", None, "a 2019 model from Carnegie Mellon and Google; the \"XL\" comes from Transformer-XL, "
                 "meaning \"extra long\"; the name has no official full form"),
                ("ERNIE-Doc", "Enhanced Representation through kNowledge IntEgration, for documents",
                 "Baidu's long-document model; holds the best peer-reviewed IMDb score (97.1%)"),
                ("LlamBERT", "LLaMA + BERT", "a 2024 method using Meta's LLaMA (Large Language Model Meta AI) to "
                 "label extra data for a BERT-style model"),
                ("large", None, "the bigger size of a model family (about 335–435 million parameters here)"),
                ("p-value", None, "the probability of seeing a difference this big if there were really no difference")],
         qa=[("Is a 0.3-point lead meaningful?",
              "The whole 95% range (97.21–97.58%) is above 97.1%, so it is unlikely to be luck on this test set. We "
              "still describe it as an extra-data result from single training runs."),
             ("Why not include RoBERTa in the ensemble?",
              "The combination was chosen on the practice set, and RoBERTa did not improve it there, so it was left out.")]),
    dict(n=14, title="How the record was built",
         one="The practical recipe behind the 97.40%.",
         says=["<b>Data:</b> official 20,000 training reviews + 1 million cleaned pool reviews; tokens prepared on cheap "
               "CPU machines; long reviews cut to their first 128 + last 382 tokens.",
               "<b>Training:</b> RoBERTa-large, ELECTRA-large, DeBERTa-v3-large; one epoch, bf16, AdamW, batch 32; "
               "checkpoints and hard time limits on every run.",
               "<b>Combining:</b> long reviews re-read in sliding windows (kept only where it helped on validation); "
               "stacking chosen by 5-fold cross-validation on val_pool; test scored once.",
               "Footer: Modal H100 80 GB GPUs, about 400 reviews per second for RoBERTa-large (about 100× the laptop). "
               "Total cost $17.99 of $30 in free credits."],
         means=["Models read text as <b>tokens</b> (word pieces) and can take at most 512 at once. For longer reviews "
                "we keep the start and the end, where people usually state their verdict.",
                "<b>One epoch</b> means the model saw each of the 1,020,000 reviews once. <b>Batch 32</b> means it learns "
                "from 32 reviews at a time. <b>bf16</b> is a shorter number format that makes the graphics card faster.",
                "<b>Checkpoints</b> save progress so a run can resume after an interruption; <b>hard time limits</b> stop "
                "any run from spending more than planned.",
                "<b>5-fold cross-validation</b>: the practice set is split into 5 parts; the stacking model is trained on "
                "4 and checked on the 5th, five times over, so every choice is scored on data it did not learn from."],
         analogy=["Tokens are LEGO bricks: long or rare words are built from several bricks.",
                  "Head + tail truncation is reading the first and last pages of a long review, where the opinion usually is.",
                  "A sliding window is reading a long scroll through a window you slide along, so you see every part.",
                  "One epoch is reading the whole textbook once; a checkpoint is a save point in a video game."],
         terms=[("Token", None, "a word or word piece; the unit a transformer reads"),
                ("Epoch", None, "one full pass through all the training data"),
                ("Batch", None, "the number of examples processed together in one learning step"),
                ("bf16", "bfloat16, \"brain floating point\" 16-bit",
                 "a compact number format from Google Brain, faster on modern GPUs with little accuracy loss"),
                ("AdamW", "Adam with decoupled Weight decay",
                 "the standard training method (optimiser); Adam = Adaptive Moment Estimation"),
                ("Cross-validation", None, "rotating which part of the data is held out for checking"),
                ("H100", None, "NVIDIA's data-centre GPU (\"Hopper\" generation) with 80 GB of memory"),
                ("GB", "gigabyte", "about a billion bytes (1,024 MB)"),
                ("Modal", None, "a cloud service that rents GPUs by the second"),
                ("CPU / GPU", "Central / Graphics Processing Unit", "general-purpose processor / massively parallel processor")],
         qa=[("Why only one epoch?",
              "With a million examples, one pass is already a lot of learning, and it kept cost and time down. "
              "Accuracy was still rising slightly at the end, so more training might add a little."),
             ("Why the cloud instead of the laptop?",
              "RoBERTa-large trains at about 3.6 reviews per second on the laptop and about 400 on an H100. A run "
              "that takes 45 minutes in the cloud would take days on the laptop.")]),
    dict(n=15, title="What we can claim, and what we can't",
         one="Stating the result honestly: the claim, and its limits.",
         says=["<b>Can claim:</b> 97.40% using about 1 million extra rating-labelled IMDb reviews, de-duplicated and "
               "movie- and author-disjoint from test; significantly better than our best single model (p = 0.046) and "
               "the official-data baseline (p ≈ 6 × 10<super>-22</super>); 95% interval above ERNIE-Doc's 97.1%.",
               "<b>Caveats:</b> an extra-training-data result; one training run per model; about 2.9% of IMDb test "
               "labels are wrong, so about 97% is the practical ceiling; energy figures use placeholder timings."],
         means=["Leaderboards separate results that used only the official training data from results that used extra "
                "data. Ours is in the second group, and saying so up front prevents an unfair comparison.",
                "<b>p ≈ 6 × 10<super>-22</super></b> is a number so small it is effectively zero: the improvement over the "
                "official-data model is certainly not luck.",
                "<b>Label errors:</b> researchers checked the IMDb test set and found at least 725 of the 25,000 labels "
                "are wrong (2.9%). A perfect reader would be \"marked wrong\" on those, so about 97% is the realistic "
                "ceiling, and any claim near 99% would suggest leakage.",
                "<b>One run per model</b>: training has some randomness; repeating with different random starts "
                "(\"seeds\") would show how stable the result is."],
         analogy=["Like an athlete saying \"fastest time in the extra-equipment category\" rather than \"world record\".",
                  "The label errors are an answer key with mistakes: even a perfect student loses those marks."],
         terms=[("Baseline", None, "the reference model you compare against; here RoBERTa-large on official data only"),
                ("Seed", None, "the starting value of a random number generator; changing it gives a different training run"),
                ("Label error", None, "a test example whose official answer is wrong"),
                ("10<super>-22</super>", None, "0.0000000000000000000001: a decimal point followed by 21 zeros then a 1")],
         qa=[("Could the 97.40% be leakage after all?",
              "Every check points the other way: copies removed, movie- and author-disjoint data, a de-duplicated test score "
              "that is unchanged, and a single test evaluation. We will also release the cleaning code."),
             ("Why not claim the record outright?",
              "Because the published best used only official data. Claiming more than we can support would undo the "
              "credibility the cleaning work earned.")]),
    dict(n=16, title="Tech stack and engineering lessons",
         one="The tools we used, and the three problems that cost the most time.",
         says=["Python 3.12, PyTorch 2.14 (Apple GPU locally, CUDA in the cloud); Hugging Face transformers 5.20; "
               "scikit-learn 1.9; Modal H100 GPUs; pyarrow and ijson for streaming 23 million reviews in 18 GB of RAM; "
               "Kaggle and Hugging Face data.",
               "Lessons: DeBERTa loaded in float16 and turned every weight into NaN (fix: force float32); Apple GPUs "
               "recompile for each input length (fix: pad to multiples of 64); public scrapes contain the benchmark "
               "(fix: always de-duplicate)."],
         means=["<b>Python</b> is the programming language; <b>PyTorch</b> runs neural networks; <b>transformers</b> "
                "provides the pretrained models; <b>scikit-learn</b> does classic machine learning (the tiny model, "
                "stacking); <b>pyarrow</b> and <b>ijson</b> read huge files in pieces so they fit in memory.",
                "<b>float16 bug:</b> one model's file was stored in a short number format. During training, tiny "
                "numbers rounded to zero, the maths divided by zero, and every value became \"Not a Number\". Loading it "
                "in the longer float32 format fixed it.",
                "<b>Apple GPU recompiling:</b> Apple's graphics chip prepares a new plan for every new input length. "
                "Rounding lengths up to multiples of 64 means only 8 sizes, each prepared once."],
         analogy=["float16 is a ruler with coarse markings: very small amounts round down to zero, and dividing by "
                  "zero gives nonsense.",
                  "Recompiling is a tailor cutting a new pattern for every slightly different body size; padding to "
                  "multiples of 64 is selling only S, M and L.",
                  "Streaming data is drinking through a straw instead of tipping the whole jug into your mouth."],
         terms=[("PyTorch", None, "a free library for building and training neural networks (from Meta)"),
                ("MPS", "Metal Performance Shaders", "Apple's system for running maths on Mac graphics chips"),
                ("CUDA", "Compute Unified Device Architecture", "NVIDIA's system for running maths on its GPUs"),
                ("scikit-learn", None, "a free Python library for classic machine learning"),
                ("pyarrow", None, "the Python interface to Apache Arrow, a fast format for large tables"),
                ("ijson", "iterative JSON", "a reader that processes huge JSON files piece by piece; JSON = JavaScript "
                 "Object Notation, a common text format for data"),
                ("float16 / float32", None, "16-bit and 32-bit decimal-number formats; more bits, more precision"),
                ("NaN", "Not a Number", "the result of an impossible calculation, such as 0 ÷ 0"),
                ("RAM", "Random Access Memory", "the laptop's working memory (18 GB here)")],
         qa=[("Why did you build so much yourselves?",
              "The pieces are standard libraries; what we built is the glue: cleaning, the router, the energy model "
              "and cost-capped cloud training."),
             ("What would you do differently?",
              "Check every model's number format when loading, and pad inputs to fixed sizes from the start.")]),
    dict(n=17, title="What happens next",
         one="The four remaining steps.",
         says=["Measure real energy on an ESP32-S3, a Raspberry Pi Zero 2 W and an INA219 current sensor.",
               "Rerun the cascade and router on the cleaned data, with a stronger hub.",
               "Repeat training with more seeds, and test on corrected IMDb labels.",
               "Write up the paper and final review materials."],
         means=["The energy numbers become measurements instead of estimates. The routing results get redone with the "
                "fully cleaned data and a better hub (which should give learning to defer a fair chance). The record "
                "result gets stronger with repeated runs and with a test set whose wrong labels are corrected."],
         analogy=["We have drawn the map; next we drive the route with a real fuel gauge (the current sensor) and "
                  "check the directions a few more times (repeated seeds)."],
         terms=[("INA219", None, "a small current-and-power sensor chip made by Texas Instruments; the name is a part "
                 "number, not an acronym"),
                ("Seed", None, "the random starting point of a training run"),
                ("Corrected labels", None, "the IMDb test set with the known wrong answers fixed (from Northcutt et al. 2021)")],
         qa=[("What hardware do you still need?",
              "An ESP32-S3 development board (a few dollars), a Raspberry Pi Zero 2 W ($15) and an INA219 sensor (about $5).")]),
]


def part3():
    rows = [["Term", "Stands for", "What it means", "Analogy"]]
    g = [
        ("ACL", "Association for Computational Linguistics", "the main research society for language technology; ERNIE-Doc was published at its 2021 conference", "the \"Olympics\" of language AI research"),
        ("AdamW", "Adam with decoupled Weight decay (Adam = Adaptive Moment Estimation)", "the method that adjusts a model's weights during training", "a driving instructor who adjusts how hard to correct each mistake"),
        ("AI", "Artificial Intelligence", "computer systems that perform tasks normally needing human judgement", "—"),
        ("Batch", "—", "how many examples the model learns from in one step (32 here)", "marking exam papers in stacks of 32"),
        ("BERT", "Bidirectional Encoder Representations from Transformers", "Google's 2018 model that reads text in both directions", "a reader who looks at words before and after each word"),
        ("bf16", "bfloat16 (\"brain floating point\", 16-bit)", "a compact number format that speeds up GPUs", "writing numbers with fewer decimal places to work faster"),
        ("Cascade", "—", "cheap model first, expensive model only when needed", "triage nurse, then specialist"),
        ("CC0", "Creative Commons Zero", "a licence placing data in the public domain", "a \"free to take\" sign"),
        ("CI", "Confidence Interval", "a range that very likely contains the true value", "\"52%, give or take 2%\" in a poll"),
        ("CPU", "Central Processing Unit", "the main general-purpose processor", "one expert chef"),
        ("Cross-validation", "—", "rotating which part of the data is held back for checking", "five mock exams, each using a different fifth of the questions"),
        ("CUDA", "Compute Unified Device Architecture", "NVIDIA's software for running maths on its GPUs", "the instruction manual for NVIDIA's kitchen"),
        ("De-duplication", "—", "removing copies and near-copies", "removing photocopies of the exam from the revision pile"),
        ("DeBERTa", "Decoding-enhanced BERT with disentangled Attention", "Microsoft's model that treats word meaning and position separately", "reading what a word means and where it sits as two separate clues"),
        ("DistilBERT", "distilled BERT", "a smaller, faster student copy of BERT", "a student who learned from a top teacher's notes"),
        ("ELECTRA", "Efficiently Learning an Encoder that Classifies Token Replacements Accurately", "Stanford and Google's model, trained to spot swapped words", "a proofreader trained to spot planted typos"),
        ("Ensemble", "—", "several models combined into one answer", "a panel of judges"),
        ("Epoch", "—", "one full pass through the training data", "reading the textbook once cover to cover"),
        ("ERNIE-Doc", "Enhanced Representation through kNowledge IntEgration, for documents", "Baidu's long-document model; best peer-reviewed IMDb score (97.1%)", "the current record holder"),
        ("ESP32-S3", "product name (Espressif Systems)", "a cheap microcontroller with 512 KB RAM and Wi-Fi", "a calculator-sized brain"),
        ("float16 / float32", "16-bit / 32-bit floating point", "number formats with less or more precision", "a ruler with coarse or fine markings"),
        ("GB / MB / KB", "gigabyte / megabyte / kilobyte", "storage sizes; each is 1,024 of the next smaller", "a library / a bookshelf / a single book"),
        ("GPU", "Graphics Processing Unit", "a processor with thousands of small cores, ideal for AI", "a kitchen with a thousand line cooks"),
        ("H100", "NVIDIA product name (\"Hopper\" generation)", "a data-centre GPU with 80 GB of memory", "an industrial kitchen for rent"),
        ("Hashing", "—", "turning text into a number with a fixed formula", "a cloakroom ticket number"),
        ("HRI", "Human-Robot Interaction", "the study of how robots and people work together", "—"),
        ("Hub", "—", "the nearby device that answers the hard cases", "the specialist doctor"),
        ("IMDb", "Internet Movie Database", "the movie website whose reviews form the benchmark", "—"),
        ("INA219", "part number (Texas Instruments)", "a sensor chip that measures current and power", "an electricity meter for a tiny device"),
        ("int8", "8-bit integer", "a whole number from −128 to 127, stored in one byte", "rounding prices to whole rupees"),
        ("IoT", "Internet of Things", "everyday devices with small computers and network connections", "—"),
        ("JSON", "JavaScript Object Notation", "a common text format for data", "a neatly labelled form"),
        ("Leakage", "—", "test answers getting into training data", "seeing the exam before sitting it"),
        ("Learning to defer", "—", "a router trained to predict whether sending will help", "a nurse who learns which cases the specialist fixes"),
        ("LLaMA / LlamBERT", "Large Language Model Meta AI / LLaMA + BERT", "Meta's language model / a method using it to label data for BERT", "—"),
        ("LLM", "Large Language Model", "a very large text model such as ChatGPT or LLaMA", "—"),
        ("Logistic regression", "—", "weighs features and outputs a probability", "a balance scale"),
        ("LoRa", "Long Range", "a low-power radio for small messages over kilometres", "a walkie-talkie for texts"),
        ("mA", "milliampere", "a thousandth of an ampere (current)", "how fast water flows through a pipe"),
        ("McNemar test", "named after Quinn McNemar", "compares two models on the same questions they disagree on", "comparing two students only on questions they answered differently"),
        ("Meshtastic", "—", "open-source off-grid text messaging over LoRa", "passing notes person to person"),
        ("mJ", "millijoule", "a thousandth of a joule (energy)", "coins spent per review"),
        ("ML", "Machine Learning", "teaching computers from examples", "learning by practice instead of rules"),
        ("Modal", "—", "a cloud service renting GPUs by the second", "a taxi instead of buying a car"),
        ("MPS", "Metal Performance Shaders", "Apple's system for maths on Mac GPUs", "Apple's kitchen manual"),
        ("ms", "millisecond", "a thousandth of a second", "—"),
        ("n-gram", "—", "a run of n words, such as \"not good\"", "a sticker made of two words"),
        ("Naive Bayes", "named after Thomas Bayes", "scores words by how much more often they appear in positive reviews", "knowing \"delicious\" appears mostly in good restaurant reviews"),
        ("NaN", "Not a Number", "the result of an impossible calculation", "a calculator showing \"Error\""),
        ("NeurIPS", "Conference on Neural Information Processing Systems", "a top AI research conference (XLNet was published there)", "—"),
        ("NLP", "Natural Language Processing", "AI that works with human language", "—"),
        ("p-value", "probability value", "chance of a difference this big if there were really none", "how surprising a coin landing heads 9 times out of 10 is"),
        ("PDF / PPT", "Portable Document Format / PowerPoint", "document file / slide deck file", "—"),
        ("Perfect router", "also \"oracle\"", "an impossible router that knows the answers; an upper bound", "a teacher who already knows which answers are wrong"),
        ("Quantization", "—", "storing numbers with less precision to save space", "rounding to fit a smaller notebook"),
        ("RAM", "Random Access Memory", "working memory where running programs live", "the size of your desk"),
        ("Raspberry Pi Zero 2 W", "W = wireless", "a $15 Linux computer with Wi-Fi and Bluetooth", "a pocket-sized PC"),
        ("RoBERTa", "Robustly Optimized BERT Pretraining Approach", "Meta's improved retraining of BERT", "the same student, given better study habits"),
        ("Seed", "—", "the random starting point of a training run", "shuffling a deck differently before dealing"),
        ("Sliding window", "—", "reading a long text in overlapping chunks", "reading a scroll through a moving window"),
        ("Stacking", "—", "a small model that learns how much to trust each ensemble member", "a head judge"),
        ("STT", "Speech-To-Text", "turning speech into written text", "a live captioner"),
        ("Test set", "—", "the data used once for the final grade", "the sealed final exam"),
        ("TF-IDF", "Term Frequency–Inverse Document Frequency", "word counts weighted towards distinctive words", "a highlighter for telling words"),
        ("Token", "—", "a word or word piece a model reads", "a LEGO brick"),
        ("Transformer", "—", "a neural network that reads all words together with \"attention\"", "a reader who sees the whole sentence at once"),
        ("V / W", "volt / watt", "electrical pressure / power (energy per second)", "water pressure / how much water flows per second"),
        ("VADER", "Valence Aware Dictionary and sEntiment Reasoner", "rule-based sentiment from a scored word list", "a dictionary of word moods"),
        ("val_pool", "validation pool", "our 50,000-review practice set from held-out movies", "the mock exams"),
        ("Validation set", "—", "data for making choices, separate from the test set", "practice papers"),
        ("Wi-Fi", "brand name (not an acronym)", "wireless networking; \"Wireless Fidelity\" is a myth", "—"),
        ("XLNet", "no official full form (\"XL\" from Transformer-XL, \"extra long\")", "a 2019 model; 96.80% on IMDb", "—"),
    ]
    rows += [list(r) for r in g]
    return [PageBreak(), P("PART 3", "eyebrow"), P("Glossary: every acronym and term, A to Z", "h1"),
            P("\"—\" means the term is not an acronym, or that no analogy is needed.", "small"), Spacer(1, 6),
            table(rows, [30 * mm, 42 * mm, 58 * mm, CONTENT_W - 130 * mm])]


def part4():
    rows = [["Number", "What it is", "Why it matters"]]
    nums = [
        ("97.40%", "Our ensemble's IMDb test accuracy", "Above the best published 97.1%, in the extra-data category"),
        ("97.21–97.58%", "95% confidence interval for 97.40%", "The whole range is above 97.1%"),
        ("97.1%", "ERNIE-Doc, best peer-reviewed IMDb result (ACL 2021)", "The record we compare against"),
        ("96.80% / 96.68%", "XLNet / LlamBERT published scores", "Other strong published results"),
        ("96.54%", "Our RoBERTa-large on official data only", "Matches the published figure, proving the setup"),
        ("97.21 / 97.22 / 97.33%", "RoBERTa / ELECTRA / DeBERTa with 1M extra reviews", "Extra data adds about 0.7 points"),
        ("p = 0.046", "Ensemble vs best single model (McNemar)", "Below 0.05, so the gain is significant"),
        ("p ≈ 6 × 10<super>-22</super>", "Ensemble vs official-data baseline", "Effectively zero: certainly not luck"),
        ("2.9% (725 reviews)", "Known wrong labels in the IMDb test set", "Sets a practical ceiling near 97%"),
        ("91% / 23,636", "Share / number of test reviews found in the download", "Why the leakage audit was essential"),
        ("5,571,499", "IMDb reviews downloaded from Kaggle", "Raw extra data"),
        ("4.1M → 3.34M", "Clean reviews after round 1 → after round 2", "Movie- and author-disjoint from test"),
        ("163,409 / 635,853 / 443", "Removed: test-movie reviews / test-author reviews / near-duplicates", "Round 2 of cleaning"),
        ("17.3M → 12.0M", "Amazon Movies &amp; TV reviews, raw → clean", "Tested; did not help, so left out"),
        ("50,000", "Size of val_pool, the practice set", "All choices were made on it"),
        ("25,000", "Size of the official IMDb test set", "Scored once for the final ensemble"),
        ("1,000,000", "Extra reviews used to train each large model", "The main source of the gain"),
        ("256 KB / 512 KB", "Tiny model size / ESP32-S3 working memory", "The model fits with room to spare"),
        ("92.32% / 92.80%", "256 KB / 1 MB model test accuracy (cleaned data)", "The on-device accuracy"),
        ("90.2% → 92.8%", "Tiny model, 20k → 1.94M training reviews (validation)", "More data beats more size"),
        ("93.51%", "DistilBERT hub accuracy (first round)", "The hub in the cascade experiments"),
        ("94.05% at 10.7%", "Cascade accuracy and share sent, threshold chosen on validation", "Beats both models alone"),
        ("~5%", "Share of reviews sent needed to match the hub", "Most reviews never leave the device"),
        ("4.1% / 3.9%", "Hub fixes / breaks the chip's answers", "Why learning to defer had little to learn"),
        ("300.6 / 15.8 / 0.8 mJ", "Energy per review: send all / cascade / device only", "The 19× saving"),
        ("14–19×", "Energy saving across hub waits of 0.1–2 s", "Robust to the placeholder timing"),
        ("283 / 88 / 51.2 mA", "Wi-Fi transmit / receive / processor current at 3.3 V", "From the ESP32-S3 datasheet"),
        ("16.6–54.6%", "Share of robot power used by motors", "Computing is a big share of robot energy"),
        ("~400 vs ~3.6 reviews/s", "RoBERTa-large training speed: H100 vs laptop", "Why training moved to the cloud"),
        ("$17.99 of $30", "Cloud cost of the record attempt", "Covered by free credits"),
    ]
    rows += [list(r) for r in nums]
    return [PageBreak(), P("PART 4", "eyebrow"), P("Numbers cheat sheet", "h1"), Spacer(1, 4),
            table(rows, [38 * mm, 70 * mm, CONTENT_W - 108 * mm])]


def part5():
    qa = [
        ("\"Isn't 97.40% suspiciously high?\"",
         "It is 0.3 points above the best published result, below the ~97% ceiling set by wrong labels, and the extra "
         "data was cleaned of every test review, test-movie review and test-author review. The de-duplicated test score "
         "is unchanged, and the test set was used once."),
        ("\"You used extra data. Isn't that unfair?\"",
         "It would be if we hid it. We report it as an extra-data result, which is a recognised category (LlamBERT is in "
         "it too), and we also report our official-data-only score (96.54%), which matches the published figure."),
        ("\"Your energy numbers are guesses.\"",
         "The currents come from the manufacturer's datasheet; only the timings are estimates. The conclusion holds "
         "across a wide range of timings, and measuring with an INA219 sensor is our next step."),
        ("\"Learning to defer didn't work, so what is your contribution?\"",
         "The system design and its measured results: the cascade matches the transformer while sending about 5% of "
         "reviews, saving 14–19× energy, plus a careful leakage audit and a record-level accuracy. Learning to defer is "
         "an honest negative result with a clear explanation and a planned rerun."),
        ("\"Why not use ChatGPT or another LLM?\"",
         "They are far too large for a device, they need the internet, and studies suggest some LLMs have seen the IMDb "
         "test set during their training, so their scores on it cannot be trusted."),
        ("\"Why IMDb?\"",
         "It is the standard benchmark with published results to compare against, and it has long reviews that make "
         "the problem realistic."),
        ("\"Can the tiny model really run on a $5 chip?\"",
         "Its weights are 256 KB and it needs only hashing and additions, no vocabulary. The next step is running it on "
         "a real ESP32-S3 board to confirm speed and energy."),
    ]
    flow = [PageBreak(), P("PART 5", "eyebrow"), P("The hardest questions, with honest answers", "h1"), Spacer(1, 4)]
    for q, a in qa:
        flow.append(KeepTogether([P(f"<b>{q}</b>"), P(a), Spacer(1, 4)]))
    return flow


def build():
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16 * mm,
                          bottomMargin=18 * mm, title="Notes: Energy-Aware Hybrid Sentiment Analysis",
                          author="Ehsan Abdulkhader, Danyson Antony, Aditya Achar")
    frame = Frame(MARGIN, 18 * mm, CONTENT_W, PAGE_H - 34 * mm, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=on_page)])
    story = cover() + part1() + [P("PART 2", "eyebrow"), P("Slide by slide", "h1"), Spacer(1, 4)]
    for s in SLIDES:
        story += slide_section(s["n"], s["title"], s["one"], s["says"], s["means"], s["analogy"], s["terms"], s["qa"])
    story += part3() + part4() + part5()
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
