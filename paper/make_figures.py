"""Figures and the energy table for the IEEE paper (paper/build_paper.py).

Sized for one IEEE column (3.5 in) with 8 pt Times labels. Reads the deferral
results and prediction files written by src/defer_router.py; the energy
operating points are chosen on val (target = a share of the chip-hub gap on
val, threshold = that send rate's val quantile) and then applied once to test.

    .venv/bin/python -I paper/make_figures.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib  # noqa: E402
import numpy as np  # noqa: E402

from common import OUT_DIR, load_proba, load_split  # noqa: E402
from defer_router import RATES, accuracy_at_rate, breakdown  # noqa: E402
from energy_curves import PARAMS, energy_per_review  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

FIG = Path(__file__).resolve().parent / "figures"
HUBS = [  # (tag, chip prefix, hub prefix, label)
    ("v1_distilbert20k", "chip", "bert", "DistilBERT, 20k reviews"),
    ("distilbert_1m", "ngram256KB", "distilbert_1m", "DistilBERT, +1M reviews"),
    ("roberta_base_1m", "ngram256KB", "roberta_base_1m", "RoBERTa-base, +1M reviews"),
]
INK, INK2, GRID = "#111111", "#555555", "#dddddd"
BLUE, ORANGE, GREEN = "#1f5fbf", "#d9601a", "#2e8b57"
T_WAIT = PARAMS["t_wait"]["value"]

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.linewidth": 0.6, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "savefig.dpi": 600,
})


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def system_diagram():
    fig, ax = plt.subplots(figsize=(3.5, 1.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.4)
    ax.axis("off")

    def box(x, y, w, h, title, lines, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
                                    fc="white", ec=color, lw=0.9))
        ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=6.5, weight="bold", color=INK)
        for i, line in enumerate(lines):
            ax.text(x + w / 2, y + h - 0.9 - i * 0.5, line, ha="center", va="top", fontsize=6, color=INK2)

    box(0.1, 0.35, 5.0, 3.7, "Device: ESP32-S3 (battery)",
        ["hash word 1-2-grams", "chip model (256 KB int8): p(x)",
         "deferral model (128 KB): g(x)", "send only if g(x) > \u03bb", "else answer locally"], BLUE)
    box(6.7, 0.95, 4.2, 2.5, "Hub: Pi Zero 2 W",
        ["transformer, int8", "(DistilBERT or RoBERTa-base)", "returns the label"], ORANGE)
    ax.add_patch(FancyArrowPatch((5.2, 2.6), (6.6, 2.6), arrowstyle="-|>", mutation_scale=7, lw=0.8, color=INK))
    ax.add_patch(FancyArrowPatch((6.6, 1.7), (5.2, 1.7), arrowstyle="-|>", mutation_scale=7, lw=0.8, color=INK))
    ax.text(5.9, 2.75, "review", ha="center", va="bottom", fontsize=6, color=INK2)
    ax.text(5.9, 1.55, "label", ha="center", va="top", fontsize=6, color=INK2)
    fig.savefig(FIG / "fig1_system.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def routing_curves():
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 3.9), sharex=True)
    for ax, (tag, _, _, label), letter in zip(axes, (HUBS[0], HUBS[2]), "ab"):
        d = json.loads((OUT_DIR / f"defer_results_{tag}.json").read_text())
        c = d["curves_test"]
        x = np.asarray(c["rates"]) * 100
        ax.plot(x, np.asarray(c["oracle"]) * 100, color=INK2, lw=0.9, ls=(0, (1, 1.5)), label="Perfect router")
        ax.plot(x, np.asarray(c["confidence"]) * 100, color=ORANGE, lw=1.2, label="Confidence routing")
        ax.plot(x, np.asarray(c["learned"]) * 100, color=BLUE, lw=1.2, ls=(0, (4, 1.5)), label="Learned deferral")
        hub = d["hub_test_accuracy"] * 100
        ax.axhline(hub, color=INK2, lw=0.6, ls=(0, (3, 2)))
        lx, ha = (59, "right") if letter == "a" else (12, "left")  # clear of the curves
        ax.text(lx, hub - 0.08, f"hub alone {hub:.2f}%", ha=ha, va="top", fontsize=6.5, color=INK2)
        ax.set_xlim(0, 60)
        ax.set_ylim(d["chip_test_accuracy"] * 100 - 0.3, max(c["oracle"]) * 100 + 0.3)
        ax.set_ylabel("Test accuracy (%)")
        ax.set_title(f"({letter}) Hub: {label}", loc="left", fontsize=8, color=INK, pad=3)
        style(ax)
    axes[1].legend(frameon=False, loc="lower right", handlelength=2.2)
    axes[1].set_xlabel("Reviews sent to the hub (%)")
    fig.tight_layout(h_pad=0.8)
    fig.savefig(FIG / "fig2_routing.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def energy_frontier():
    fig, ax = plt.subplots(figsize=(3.5, 2.35))
    for (tag, _, _, label), color in zip(HUBS, (INK2, ORANGE, BLUE)):
        d = json.loads((OUT_DIR / f"defer_results_{tag}.json").read_text())
        rates = np.asarray(d["curves_test"]["rates"])
        e = np.array([energy_per_review(s, T_WAIT) * 1000 for s in rates])
        ax.plot(e, np.asarray(d["curves_test"]["confidence"]) * 100, color=color, lw=1.2, label=label)
    ax.set_xscale("log")
    ax.set_xlim(0.7, 400)
    ax.set_xticks([1, 3, 10, 30, 100, 300], ["1", "3", "10", "30", "100", "300"])
    ax.axvline(energy_per_review(1.0, T_WAIT) * 1000, color=INK2, lw=0.6, ls=(0, (3, 2)))
    ax.text(290, 92.5, "send\nevery\nreview", ha="right", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xlabel("Device energy per review (mJ, log scale)")
    ax.set_ylabel("Test accuracy (%)")
    ax.legend(frameon=False, loc="upper left", title="Confidence routing to:", title_fontsize=7)
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_energy.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def energy_table():
    """Send rates chosen on val to close a share of the chip-hub gap; applied once to test."""
    y_val, y_test = load_split("val")["label"].to_numpy(), load_split("test")["label"].to_numpy()
    send_all = energy_per_review(1.0, T_WAIT) * 1000
    rows = []
    for tag, chip, hub, label in HUBS:
        pc = {s: load_proba(chip, s) for s in ("val", "test")}
        ph = {s: load_proba(hub, s) for s in ("val", "test")}
        score = {s: 1 - np.maximum(pc[s], 1 - pc[s]) for s in ("val", "test")}
        chip_val = float(((pc["val"] >= 0.5) == y_val).mean())
        hub_val = float(((ph["val"] >= 0.5) == y_val).mean())
        val_acc = [accuracy_at_rate(score["val"], pc["val"], ph["val"], y_val, r) for r in RATES]
        for share in (0.5, 0.75, 0.9):
            target = chip_val + share * (hub_val - chip_val)
            rate = float(next(r for r, a in zip(RATES, val_acc) if a >= target - 1e-12))
            thr = np.quantile(score["val"], 1 - rate)
            b = breakdown(score["test"] > thr, pc["test"], ph["test"], y_test)
            mj = energy_per_review(b["sent_share"], T_WAIT) * 1000
            rows.append({"hub": label, "gap_share": share, "val_rate": rate, "test_sent": b["sent_share"],
                         "test_accuracy": b["accuracy"], "mJ": mj, "saving_vs_send_all": send_all / mj})
    return {"t_wait_s": T_WAIT, "send_all_mJ": send_all,
            "chip_only_mJ": energy_per_review(0.0, T_WAIT) * 1000, "rows": rows}


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    system_diagram()
    routing_curves()
    energy_frontier()
    table = energy_table()
    (Path(__file__).resolve().parent / "energy_table.json").write_text(json.dumps(table, indent=2))
    for r in table["rows"]:
        print(f"{r['hub']:28s} {r['gap_share']:.0%} of gap: val rate {r['val_rate']:.2f}, test sent {r['test_sent']:.1%}, "
              f"test acc {r['test_accuracy']:.4f}, {r['mJ']:.1f} mJ ({r['saving_vs_send_all']:.1f}x less)")


if __name__ == "__main__":
    main()
