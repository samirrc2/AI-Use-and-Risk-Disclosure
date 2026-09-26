"""Render the two figures printed in the article, at publication resolution.

analyze.py draws the same data in a plain screen style at 150 dpi. The versions typeset in
the manuscript are a journal rendering of those figures: a serif face to match the body text,
hatching so the two series survive greyscale printing, printed values, and 300 dpi. Until
this existed no committed code produced them, so the published figures were the one part of
the article that could not be regenerated from the capsule.

Everything is read from the same frozen tables analyze.py writes, so the figures and the
numbers in the text cannot drift apart.

Outputs: results/figures/publication/figure1.png, figure2.png
"""
from __future__ import annotations
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import io_paths

DPI = 300
BLUE = "#1f6fa8"
ORANGE = "#d4821a"
GREY = "#93a1bc"

# Bundled with matplotlib, so the render does not depend on fonts installed on the host.
STYLE = {
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 13,
    "axes.linewidth": 1.1,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "svg.hashsalt": "p10",          # deterministic ids
}


def _tables():
    return io_paths.out_dir() / "tables"


def figure1(dest):
    """Disclosed any-use by adviser type and AUM quartile (article Figure 1)."""
    with open(_tables() / "table2_gradient.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    qs = ["Q1", "Q2", "Q3", "Q4"]
    pf = [100 * float(r["any_use"]) for q in qs for r in rows
          if r["type"] == "private_fund" and r["aum_quartile"] == q]
    wr = [100 * float(r["any_use"]) for q in qs for r in rows
          if r["type"] == "wealth_ria" and r["aum_quartile"] == q]
    if len(pf) != 4 or len(wr) != 4:
        sys.exit("ERROR: table2_gradient.csv does not hold 4 quartiles for both adviser types")

    x = range(4)
    w = 0.38
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    b1 = ax.bar([i - w / 2 for i in x], pf, w, color=BLUE, label="Private-fund")
    b2 = ax.bar([i + w / 2 for i in x], wr, w, color=ORANGE, hatch="///",
                edgecolor="white", linewidth=0, label="Wealth/retail")
    for bars, vals in ((b1, pf), (b2, wr)):
        for rect, v in zip(bars, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, v + 1.2, f"{round(v):.0f}",
                    ha="center", va="bottom")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["Q1\n(smallest)", "Q2", "Q3", "Q4\n(largest)"])
    ax.set_xlabel("Assets-under-management quartile")
    ax.set_ylabel("Disclosed any-use (%)")
    ax.set_ylim(0, max(pf + wr) * 1.18)
    ax.legend(frameon=False, loc="upper left")
    fig.savefig(dest, dpi=DPI)
    plt.close(fig)
    return pf, wr


def figure2(dest):
    """Disclosed any-use by venue for the matched firms (article Figure 2)."""
    with open(_tables() / "table5_venue.json", encoding="utf-8") as fh:
        v = json.load(fh)
    n = int(v["n_firms_both_venues"])
    vals = [100 * float(v["brochure_anyuse"]), 100 * float(v["marketing_anyuse"])]

    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    bars = ax.bar(["Fiduciary\nbrochure", "Website\nmarketing"], vals,
                  width=0.56, color=[BLUE, GREY])
    for rect, val in zip(bars, vals):
        ax.text(rect.get_x() + rect.get_width() / 2, val + 0.7, f"{val:.1f}%",
                ha="center", va="bottom")
    ax.set_ylabel("Disclosed any-use (%)")
    ax.set_title(f"Disclosure by venue (n = {n} matched firms)", fontsize=12.5, pad=10)
    ax.set_ylim(0, max(vals) * 1.22)
    fig.savefig(dest, dpi=DPI)
    plt.close(fig)
    return vals, n


def main():
    out = io_paths.out_dir() / "figures" / "publication"
    out.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(STYLE):
        pf, wr = figure1(out / "figure1.png")
        vals, n = figure2(out / "figure2.png")
    print(f"[pubfig] figure1.png  private-fund {[round(v) for v in pf]}  "
          f"wealth/retail {[round(v) for v in wr]}")
    print(f"[pubfig] figure2.png  brochure {vals[0]:.1f}%  website {vals[1]:.1f}%  n={n}")
    print(f"[pubfig] wrote {out}")


if __name__ == "__main__":
    main()
