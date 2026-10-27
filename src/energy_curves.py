"""Phase 6: what each router costs in device energy.

Energy the battery-powered device spends per review:

    E(s) = V * ( I_cpu * t_local  +  s * ( I_tx * t_tx + I_rx * t_wait ) )

s is the share of reviews sent to the hub. Currents come from the ESP32-S3
datasheet (v2.2, Tables 5-7 and 5-9). The three timings are PLACEHOLDERS
until measured on the real board: they are written into every output, and
the hub wait time is swept because it depends on the hub hardware.

Idle and sleep power between reviews is not included: this is energy per
review, not battery life.

Reads outputs/defer_results{_tag}.json (accuracy vs send rate on the test split).

    python -I src/energy_curves.py [--tag roberta_base_1m]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

import matplotlib  # noqa: E402
import numpy as np  # noqa: E402

from common import OUT_DIR, save_json  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PARAMS = {
    "V": {"value": 3.3, "unit": "V", "source": "ESP32-S3 datasheet v2.2, measurement supply (Sec. 5.6)"},
    "I_cpu": {"value": 0.0512, "unit": "A", "source": "datasheet Table 5-9: 240 MHz, one core active, Typ1"},
    "I_tx": {"value": 0.283, "unit": "A", "source": "datasheet Table 5-7: 802.11n HT20 MCS7 @18.5 dBm, peak"},
    "I_rx": {"value": 0.088, "unit": "A", "source": "datasheet Table 5-7: RX 802.11b/g/n HT20"},
    "t_local": {"value": 0.005, "unit": "s", "source": "PLACEHOLDER: on-chip model time per review, to be measured"},
    "t_tx": {"value": 0.010, "unit": "s", "source": "PLACEHOLDER: sending one review (~1.5 KB) on an open connection"},
    "t_wait": {"value": 1.0, "unit": "s", "source": "PLACEHOLDER: radio listening while the hub answers; swept below"},
}
WAIT_SWEEP = [0.1, 0.5, 1.0, 2.0]
BATTERY_J = 2.0 * 3.7 * 3600  # illustrative 2000 mAh, 3.7 V cell (T-Deck Plus listing)


def energy_per_review(s, t_wait):
    p = {k: v["value"] for k, v in PARAMS.items()}
    return p["V"] * (p["I_cpu"] * p["t_local"] + s * (p["I_tx"] * p["t_tx"] + p["I_rx"] * t_wait))


def rate_needed(rates, accs, target):
    return next((r for r, a in zip(rates, accs) if a >= target - 1e-12), None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="", help="read defer_results_{tag}.json, write energy_*_{tag}")
    suffix = f"_{t}" if (t := p.parse_args().tag) else ""
    d = json.loads((OUT_DIR / f"defer_results{suffix}.json").read_text())
    rates, curves = np.asarray(d["curves_test"]["rates"]), d["curves_test"]
    chip, hub = d["chip_test_accuracy"], d["hub_test_accuracy"]
    targets = [round(chip + (hub - chip) * f, 4) for f in (0.5, 0.75, 1.0)]
    t_wait = PARAMS["t_wait"]["value"]
    send_all = energy_per_review(1.0, t_wait)

    table = []
    for target in targets:
        row = {"target_accuracy": target}
        for name in ("confidence", "learned"):
            s = rate_needed(rates, curves[name], target)
            e = None if s is None else energy_per_review(s, t_wait)
            row[name] = {"send_rate": s, "mJ_per_review": None if e is None else e * 1000,
                         "vs_send_all": None if e is None else e / send_all,
                         "reviews_per_charge": None if e is None else BATTERY_J / e,
                         "devices_per_hub_vs_send_all": None if not s else 1 / s}
        table.append(row)

    sweep = []
    for w in WAIT_SWEEP:
        row = {"t_wait_s": w, "send_all_mJ": energy_per_review(1.0, w) * 1000,
               "chip_only_mJ": energy_per_review(0.0, w) * 1000}
        for name in ("confidence", "learned"):
            s = rate_needed(rates, curves[name], hub)
            row[f"{name}_mJ_at_hub_accuracy"] = None if s is None else energy_per_review(s, w) * 1000
        sweep.append(row)

    save_json(f"energy_results{suffix}.json", {"params": PARAMS, "battery_J_illustrative": BATTERY_J,
                                      "chip_accuracy": chip, "hub_accuracy": hub,
                                      "send_all_mJ": send_all * 1000, "targets": table, "t_wait_sweep": sweep})
    plot(table, send_all * 1000, OUT_DIR / f"energy_bars{suffix}.png")
    for row in table:
        c, l = row["confidence"], row["learned"]
        fmt = lambda x: "n/a" if x["mJ_per_review"] is None else f"{x['mJ_per_review']:.1f} mJ ({x['send_rate']:.0%} sent)"
        print(f"accuracy >= {row['target_accuracy']:.2%}: confidence {fmt(c)} | learned {fmt(l)}")
    print(f"send everything: {send_all * 1000:.1f} mJ per review")


def plot(table, send_all_mj, path):
    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    colors = {"confidence": "#eb6834", "learned": "#2a78d6"}
    labels = {"confidence": "Confidence routing", "learned": "Learned deferral (ours)"}
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200, facecolor=surface)
    ax.set_facecolor(surface)
    x = np.arange(len(table))
    width = 0.34
    for j, name in enumerate(("confidence", "learned")):
        vals = [row[name]["mJ_per_review"] for row in table]
        xs = x + (j - 0.5) * (width + 0.02)
        ax.bar(xs, [v or 0 for v in vals], width=width, color=colors[name], label=labels[name], zorder=2)
        for xi, v, row in zip(xs, vals, table):
            text = "not reached" if v is None else f"{v:.0f} mJ\n{row[name]['send_rate']:.0%} sent"
            ax.text(xi, (v or 0) + send_all_mj * 0.01, text, ha="center", va="bottom", color=ink, fontsize=8)
    ax.axhline(send_all_mj, color=ink2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(len(table) - 0.5, send_all_mj, f"send every review  {send_all_mj:.0f} mJ", color=ink2, fontsize=9,
            ha="right", va="bottom")
    ax.set_xticks(x, [f"reach {row['target_accuracy']:.2%}" for row in table])
    ax.set_ylabel("Device energy per review (mJ)", color=ink2, fontsize=9.5)
    ax.set_title("Energy needed to reach each accuracy (test set)", loc="left", color=ink, fontsize=11, pad=22)
    p = {k: v["value"] for k, v in PARAMS.items()}
    ax.text(0, 1.02, f"Currents from ESP32-S3 datasheet; placeholder timings: local {p['t_local'] * 1000:.0f} ms, "
                     f"send {p['t_tx'] * 1000:.0f} ms, hub wait {p['t_wait']:.1f} s (to be measured)",
            transform=ax.transAxes, color=ink2, fontsize=8)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(0, send_all_mj * 1.18)
    ax.grid(axis="y", color=grid, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(grid)
    ax.tick_params(colors=ink2, labelsize=9, length=0)
    fig.tight_layout()
    fig.savefig(path, facecolor=surface)
    plt.close(fig)


if __name__ == "__main__":
    main()
