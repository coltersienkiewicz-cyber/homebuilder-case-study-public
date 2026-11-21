"""Build the case-study visuals from editable CSV inputs.

Edit the CSVs in 03_Analysis/Case_Study_Charts/data/, then run:
    python3 03_Analysis/Case_Study_Charts/build_case_study_visuals.py

The script calculates land-control percentages and waterfall steps from the
input data. Figures are written to 03_Analysis/Case_Study_Charts/outputs/.
"""

from __future__ import annotations

import csv
import math
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = ROOT / "outputs"
# Copy every chart into the deliverable folder too, so the LaTeX project (e.g. on Overleaf)
# is self-contained and never needs a ../ path.
DELIVERABLE_FIGS = ROOT.parents[1] / "01_Final_Deliverable" / "figures"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.lines import Line2D

# One type system for every chart, matching the brief (Helvetica-style sans body text).
# Figures are drawn at their PRINTED size, so these are true point sizes on the page.
COLUMN_IN = 3.4          # one column of the two-column brief
T_TITLE = 8.0            # in-chart title
T_LABEL = 7.0            # axis labels, legend, data callouts
T_TICK = 6.5             # tick labels, small notes
plt.rcParams.update({
    "font.family": "Arial",  # Helvetica metrics; macOS Helvetica.ttc exposes no bold to matplotlib
    "font.size": T_LABEL,
    "axes.titlesize": T_TITLE,
    "axes.labelsize": T_LABEL,
    "xtick.labelsize": T_TICK,
    "ytick.labelsize": T_TICK,
    "legend.fontsize": T_TICK,
    "axes.unicode_minus": False,
})


COLORS = {
    "ink": "#18324B",
    "blue": "#356B8C",
    "teal": "#3E8C83",
    "orange": "#D17A48",
    "gold": "#C7A24A",
    "purple": "#7E6A9A",
    "green": "#5B8A62",
    "red": "#B75D5D",
    "gray": "#7A8791",
    "light_gray": "#D9DEE2",
    "paper": "#FFFFFF",
    "pale": "#E8F0F4",
}


def read_csv(filename: str) -> list[dict[str, str]]:
    with (DATA / filename).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save_figure(fig: plt.Figure, filename: str) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / filename
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    DELIVERABLE_FIGS.mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_FIGS / filename).write_bytes(path.read_bytes())
    return path


def company_rows() -> list[dict[str, str]]:
    rows = read_csv("company_metrics.csv")
    if not rows:
        raise ValueError("company_metrics.csv has no company rows")
    return rows


# Same three buyer segments and colors as the customer chart (Figure 3), by each
# builder's stated buyer focus in its 10-K, so the two figures never disagree.
ARCHETYPES = {
    "Toll Brothers": "Luxury",
    "Taylor Morrison": "Move-up / mixed",
    "NVR": "Move-up / mixed",
    "PulteGroup": "Move-up / mixed",
    "Sekisui House U.S.": "Move-up / mixed",
    "D.R. Horton": "Entry-level",
    "Lennar": "Entry-level",
    "Meritage Homes": "Entry-level",
    "KB Home": "Entry-level",
    "Century Communities": "Entry-level",
}
ARCHETYPE_COLORS = {
    "Luxury": COLORS["orange"],
    "Move-up / mixed": COLORS["gray"],
    "Entry-level": COLORS["blue"],
}

# Ticker-style codes sit inside each bubble so no leader lines are needed;
# the full name / margin key belongs in the figure caption, not the chart.
TICKERS = {
    "D.R. Horton": "DHI",
    "Lennar": "LEN",
    "PulteGroup": "PHM",
    "NVR": "NVR",
    "Meritage Homes": "MTH",
    "Taylor Morrison": "TMHC",
    "KB Home": "KBH",
    "Toll Brothers": "TOL",
    "Century Communities": "CCS",
    "Sekisui House U.S.": "SHU",
}


def bubble_size(gross_margin_pct: float) -> float:
    """Marker area in pt^2 at print size; exaggerated so margin differences are visible."""
    return 30 + (gross_margin_pct - 14) * 14


def build_competitor_visual() -> Path:
    rows = company_rows()
    closings = [float(r["closings_units"]) for r in rows]
    asp = [float(r["asp_usd"]) / 1000 for r in rows]
    margin = [float(r["gross_margin_pct"]) for r in rows]

    fig, ax = plt.subplots(figsize=(COLUMN_IN, 2.3), facecolor=COLORS["paper"])
    fig.subplots_adjust(left=0.14, right=0.98, top=0.86, bottom=0.15)

    # Bubble area is exaggerated (not proportional) purely to make margin differences pop.
    nudges = {"Century Communities": (-7, 0), "Lennar": (0, 2), "D.R. Horton": (8, -3),
              "Sekisui House U.S.": (-7, 0)}
    for row, x, y, gm in zip(rows, closings, asp, margin):
        s = bubble_size(gm)
        ax.scatter(x, y, s=s, color=ARCHETYPE_COLORS[ARCHETYPES[row["company"]]], alpha=0.92,
                   edgecolor=COLORS["paper"], linewidth=0.8, zorder=3)
        r_pt = math.sqrt(s / math.pi)
        dx, dy = nudges.get(row["company"], (0, 0))
        ax.annotate(TICKERS[row["company"]], (x, y), xytext=(dx, r_pt + 1 + dy), textcoords="offset points",
                    ha="center", va="bottom", fontsize=T_TICK, fontweight="bold", color=COLORS["ink"], zorder=4)

    quad = {"transform": ax.transAxes, "fontsize": T_TICK, "fontweight": "bold", "color": COLORS["gray"]}
    ax.text(0.20, 0.97, "LUXURY /\nSPECIALTY", ha="left", va="top", **quad)
    ax.text(0.02, 0.03, "REGIONAL /\nENTRY-LEVEL", ha="left", va="bottom", **quad)
    ax.text(0.98, 0.03, "SCALE /\nVOLUME", ha="right", va="bottom", **quad)

    handles = [Line2D([0], [0], marker="o", linestyle="none", color=c, markersize=5, label=l)
               for l, c in ARCHETYPE_COLORS.items()]
    ax.legend(handles=handles, loc="upper right", frameon=False, handletextpad=0.2,
              labelspacing=0.35, borderaxespad=0.2, labelcolor=COLORS["ink"])

    ax.set_xlim(0, 102000)
    ax.set_ylim(200, 1080)
    ax.set_xlabel("Annual home closings (units)", color=COLORS["ink"], labelpad=2)
    ax.set_ylabel("Avg. selling price ($K)", color=COLORS["ink"], labelpad=2)
    ax.set_xticks([0, 25000, 50000, 75000, 100000])
    ax.set_xticklabels(["0", "25K", "50K", "75K", "100K"])
    ax.set_yticks([400, 600, 800, 1000])
    ax.grid(False)
    ax.set_axisbelow(True)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(COLORS["light_gray"])
    ax.tick_params(colors=COLORS["gray"], length=0, pad=2)

    fig.text(0.0, 0.985, "Scale, price tier and margin by builder", ha="left", va="top",
             fontsize=T_TITLE, fontweight="bold", color=COLORS["ink"])
    fig.text(0.0, 0.925, "Bubble size = homebuilding gross margin", ha="left", va="top",
             fontsize=T_TICK, color=COLORS["gray"])
    return save_figure(fig, "competitor-scale-price-margin.png")


def build_supplier_visual() -> Path:
    costs = read_csv("supplier_cost_mix.csv")
    cost_map = {r["category"].lower(): float(r["share_pct"]) for r in costs}
    construction = next(v for k, v in cost_map.items() if "construction costs" in k)
    lot = next(v for k, v in cost_map.items() if "finished lot cost" in k)
    profit = next(v for k, v in cost_map.items() if "pre-tax profit" in k)
    other = sum(v for k, v in cost_map.items()
                if k not in {"construction costs (labor and materials)", "finished lot cost", "builder pre-tax profit"})

    ink = COLORS["ink"]
    fig, (ax_wf, ax_px) = plt.subplots(1, 2, figsize=(COLUMN_IN, 1.85),
                                       gridspec_kw={"width_ratios": [1.1, 1.0]}, facecolor=COLORS["paper"])
    fig.subplots_adjust(left=0.01, right=0.80, top=0.80, bottom=0.12, wspace=0.22)

    stages = ["Price", "Build", "Lot", "Other", "Profit"]
    bottoms = [0, 100 - construction, 100 - construction - lot, 100 - construction - lot - other, 0]
    heights = [100, construction, lot, other, profit]
    colors = [COLORS["blue"], COLORS["orange"], COLORS["gold"], "#5A5A5A", COLORS["teal"]]
    for i, (bottom, height, color) in enumerate(zip(bottoms, heights, colors)):
        ax_wf.bar(i, height, bottom=bottom, width=0.74, color=color, zorder=3)
    levels = [100, 100 - construction, 100 - construction - lot, 100 - construction - lot - other]
    for i, level in enumerate(levels):
        ax_wf.plot([i + 0.37, i + 0.63], [level, level], color=ink, linewidth=0.5)
    labels = ["100%", f"{construction:.0f}%", f"{lot:.0f}%", f"{other:.0f}%", f"{profit:.0f}%"]
    for i, (bottom, height, label) in enumerate(zip(bottoms, heights, labels)):
        inside = i in (1, 2)
        ax_wf.text(i, bottom + height / 2 if inside else bottom + height + 2, label, ha="center",
                   va="center" if inside else "bottom", color="white" if inside else ink,
                   fontsize=T_TICK, fontweight="bold")
    ax_wf.text(4.4, 98, f"Build costs =\n{construction / lot:.1f}× lot costs", ha="right", va="top",
               fontsize=T_TICK, fontweight="bold", color=ink, linespacing=1.1)
    ax_wf.set_xticks(range(len(stages)), stages)
    ax_wf.set_ylim(0, 112)
    ax_wf.set_yticks([])
    ax_wf.spines[["top", "right", "left"]].set_visible(False)
    ax_wf.spines["bottom"].set_color(COLORS["light_gray"])
    ax_wf.tick_params(axis="x", length=0, colors=ink, pad=2)
    ax_wf.set_title("Cost stack, % of sale price", loc="left", fontsize=T_LABEL, fontweight="bold",
                    color=ink, pad=4)

    from datetime import date, timedelta
    import matplotlib.dates as mdates
    series: dict[str, list[tuple[date, float]]] = {}
    for r in read_csv("materials_vs_home_prices.csv"):
        series.setdefault(r["series"], []).append((date.fromisoformat(r["date"]), float(r["value"])))
    ppi, hpi = series["WPUSI012011"], series["USSTHPI"]
    ppi_base = next(v for t, v in ppi if t == date(2019, 12, 1))
    hpi_base = next(v for t, v in hpi if t == date(2019, 10, 1))  # 2019 Q4
    ppi_pts = [(t, v / ppi_base * 100) for t, v in ppi if t >= date(2019, 12, 1)]
    hpi_pts = [(t + timedelta(days=45), v / hpi_base * 100) for t, v in hpi if t >= date(2019, 10, 1)]
    ax_px.axhline(100, color=COLORS["light_gray"], linewidth=0.5)
    for name, pts, color in [("Materials", ppi_pts, COLORS["orange"]), ("Home prices", hpi_pts, COLORS["blue"])]:
        ax_px.plot([t for t, _ in pts], [v for _, v in pts], color=color, linewidth=1.2)
    (_, m_end), (_, h_end) = ppi_pts[-1], hpi_pts[-1]
    lx = max(ppi_pts[-1][0], hpi_pts[-1][0]) + timedelta(days=60)
    ax_px.text(lx, max(m_end, h_end + 9), f"Materials\n{m_end:.0f}", color=COLORS["orange"],
               fontsize=T_TICK, fontweight="bold", va="center", linespacing=1.0, clip_on=False)
    ax_px.text(lx, min(h_end, m_end - 9), f"Home\nprices {h_end:.0f}", color=COLORS["blue"],
               fontsize=T_TICK, fontweight="bold", va="center", linespacing=1.0, clip_on=False)
    ax_px.set_xlim(date(2019, 10, 1), ppi_pts[-1][0] + timedelta(days=20))
    ax_px.set_ylim(92, 175)
    ax_px.set_yticks([100, 125, 150])
    ax_px.set_xticks([date(y, 1, 1) for y in (2020, 2022, 2024, 2026)])
    ax_px.xaxis.set_major_formatter(mdates.DateFormatter("'%y"))
    ax_px.grid(axis="y", color=COLORS["light_gray"], linewidth=0.4, alpha=0.7)
    ax_px.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax_px.tick_params(axis="both", length=0, colors=COLORS["gray"], pad=2)
    ax_px.set_title("Materials vs. home prices, 2019 = 100", loc="left", fontsize=T_LABEL,
                    fontweight="bold", color=ink, pad=4)
    return save_figure(fig, "supplier-cost-stack-land-control.png")


SEGMENT_STYLE = {
    "luxury": ("Luxury", COLORS["orange"]),
    "move_up": ("Move-up / mixed", COLORS["gray"]),
    "entry": ("Entry-level", COLORS["blue"]),
}


def build_customer_visual() -> Path:
    """Latest-year revenue change by builder, grouped luxury -> entry. Drawn at 2in x 2in print size."""
    with (DATA / "luxury_vs_entry_revenue.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    years = sorted(k for k in rows[0] if k.isdigit())
    prev, last = years[-2], years[-1]
    order = list(SEGMENT_STYLE)
    for r in rows:
        r["chg"] = 100 * (float(r[last]) / float(r[prev]) - 1)
    rows.sort(key=lambda r: (order.index(r["segment"]), -r["chg"]))
    rows.reverse()  # barh draws bottom-up; put luxury on top

    fig, ax = plt.subplots(figsize=(2.0, 2.0), facecolor=COLORS["paper"])
    fig.subplots_adjust(left=0.36, right=0.97, top=0.80, bottom=0.07)
    y = list(range(len(rows)))
    colors = [SEGMENT_STYLE[r["segment"]][1] for r in rows]
    ax.barh(y, [r["chg"] for r in rows], color=colors, height=0.68, zorder=2)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.6, zorder=3)

    short = {"Century Communities": "Century", "Taylor Morrison": "Taylor Morr.", "Meritage Homes": "Meritage"}
    ax.set_yticks(y)
    ax.set_yticklabels([short.get(r["company"], r["company"]) for r in rows])
    for tick, c in zip(ax.get_yticklabels(), colors):
        tick.set_color(c)
    for yi, r in zip(y, rows):
        v = r["chg"]
        ax.text(v + (0.6 if v >= 0 else -0.6), yi, f"{v:+.0f}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=6.0, color=COLORS["ink"])

    # segment dividers
    for i in range(1, len(rows)):
        if rows[i]["segment"] != rows[i - 1]["segment"]:
            ax.axhline(i - 0.5, color=COLORS["light_gray"], linewidth=0.5)

    ax.set_xlim(-29, 8)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([])
    for side in ["top", "right", "left", "bottom"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=6.2, pad=2)

    fig.text(0.02, 0.985, "K-shaped Economy", ha="left", va="top", fontsize=T_TITLE,
             fontweight="bold", color=COLORS["ink"])
    fig.text(0.02, 0.905, "Home revenue, change in latest year", ha="left", va="top", fontsize=6.2,
             color=COLORS["gray"])
    handles = [Line2D([0], [0], marker="s", linestyle="", markersize=3.6, markerfacecolor=c,
                      markeredgewidth=0, label=label) for label, c in SEGMENT_STYLE.values()]
    fig.legend(handles=handles, frameon=False, fontsize=5.8, ncol=3, loc="upper left",
               bbox_to_anchor=(0.0, 0.865), handletextpad=0.1, columnspacing=0.6, borderaxespad=0,
               labelcolor=COLORS["gray"])
    return save_figure(fig, "customer-luxury-vs-entry.png")


def main() -> None:
    outputs = [build_competitor_visual(), build_supplier_visual(), build_customer_visual()]
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
