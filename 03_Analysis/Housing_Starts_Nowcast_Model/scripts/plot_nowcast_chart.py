"""Build the nowcast backtest/forecast chart for the case-study write-up.

Re-runs cohort_markov_nowcast.py (so the chart always reflects the current
data), then plots model-implied vs. actual total starts (SAAR) over the
recent backtest window plus the one-step-ahead forecast point. Written to
03_Analysis/Case_Study_Charts/outputs/ to sit alongside the other case-study visuals.

    python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/plot_nowcast_chart.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOWCAST_SCRIPT = ROOT / "scripts" / "cohort_markov_nowcast.py"
OUTPUT = ROOT.parent / "Case_Study_Charts" / "outputs"
DELIVERABLE_FIGS = ROOT.parents[1] / "01_Final_Deliverable" / "figures"  # self-contained LaTeX project
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd

# Same type system as 03_Analysis/Case_Study_Charts/build_case_study_visuals.py: drawn at printed size (one
# 3.4in column), Arial (Helvetica metrics), 8pt title / 7pt labels / 6.5pt ticks.
plt.rcParams.update({"font.family": "Arial", "axes.unicode_minus": False})
COLUMN_IN = 3.4

# Palette matches 03_Analysis/Case_Study_Charts/build_case_study_visuals.py so all four charts read as one set.
COLORS = {
    "ink": "#18324B",
    "blue": "#356B8C",
    "teal": "#3E8C83",
    "orange": "#D17A48",
    "gold": "#C7A24A",
    "gray": "#7A8791",
    "light_gray": "#D9DEE2",
    "paper": "#FFFFFF",
    "pale": "#E8F0F4",
}


def run_nowcast_script() -> str:
    """Regenerate cohort_markov_simulation.csv and capture the printed stats."""
    result = subprocess.run(
        [sys.executable, str(NOWCAST_SCRIPT)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_stats(stdout: str) -> dict[str, float | str]:
    def grab(pattern: str, cast=float):
        m = re.search(pattern, stdout)
        if not m:
            raise ValueError(f"Could not find pattern in nowcast output: {pattern!r}")
        return cast(m.group(1))

    return {
        "mae": grab(r"MAE:\s*([\d.]+) thousand"),
        "corr": grab(r"Correlation:\s*([\d.\-]+)"),
        "next_month": grab(r"Nowcast for (\d{4}-\d{2}) total starts", str),
        "nowcast_saar": grab(r"Total nowcast:\s*([\d.\-]+)"),
        "actual_prior_month": grab(r"\(prior month\):\s*([\d.\-]+)"),
        "actual_year_ago": grab(r"\(same month last year\):\s*([\d.\-]+)"),
    }


def main() -> None:
    stdout = run_nowcast_script()
    print(stdout)
    stats = parse_stats(stdout)

    sim = pd.read_csv(DATA / "cohort_markov_simulation.csv", comment="#", parse_dates=["date"]).set_index("date")
    window = sim.tail(48).dropna(subset=["starts_actual_saar_thousands"])
    backtest = window.tail(24)

    last_date = sim.index.max()
    forecast_date = last_date + pd.offsets.MonthBegin(1)
    nowcast = stats["nowcast_saar"]
    mae = stats["mae"]

    # Deliberately minimal: title, stats, source and error-band definition live in the
    # LaTeX figure caption, so the image carries only what you need to read the lines.
    BIG, MID = 7.0, 6.5
    fig, ax = plt.subplots(figsize=(COLUMN_IN, 2.15), facecolor=COLORS["paper"])
    ax.set_facecolor(COLORS["paper"])

    ax.axvspan(backtest.index.min(), backtest.index.max(), color=COLORS["pale"], zorder=0,
               label="Backtest window")
    ax.plot(window.index, window["starts_actual_saar_thousands"], color=COLORS["ink"],
            linewidth=0.9, marker="o", markersize=1.6, label="Actual", zorder=3)
    ax.plot(window.index, window["starts_model_saar_thousands"], color=COLORS["blue"],
            linewidth=1.4, label="Model", zorder=3)

    ax.plot([last_date, forecast_date], [window["starts_model_saar_thousands"].iloc[-1], nowcast],
            color=COLORS["orange"], linewidth=0.9, linestyle="--", zorder=3)
    ax.errorbar([forecast_date], [nowcast], yerr=[[mae], [mae]], fmt="D", color=COLORS["orange"],
                ecolor=COLORS["orange"], elinewidth=0.9, capsize=2.5, markersize=4, zorder=4,
                label="Nowcast")
    y_all = pd.concat([window["starts_actual_saar_thousands"], window["starts_model_saar_thousands"]])
    y_lo = min(y_all.min(), nowcast - mae)
    y_hi = max(y_all.max(), nowcast + mae)
    pad = (y_hi - y_lo) * 0.06
    ax.set_ylim(y_lo - pad, y_hi + pad * 1.5)
    ax.set_xlim(window.index.min() - pd.Timedelta(days=20), forecast_date + pd.Timedelta(days=60))

    y_hi_label = y_hi + pad
    ax.annotate(f"{forecast_date:%b} nowcast\n{nowcast:,.0f}k",
                (forecast_date, nowcast + mae), xytext=(forecast_date, y_hi_label),
                textcoords="data", fontsize=BIG, fontweight="bold", color=COLORS["orange"],
                ha="right", va="top", multialignment="right",
                arrowprops={"arrowstyle": "-", "color": COLORS["orange"], "linewidth": 0.6, "linestyle": ":",
                            "shrinkA": 4, "shrinkB": 4, "relpos": (1, 0)})

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}k"))
    ax.set_ylabel("Starts (annual rate)", fontsize=BIG, color=COLORS["ink"], labelpad=2)
    ax.grid(axis="y", color=COLORS["light_gray"], linewidth=0.4)
    ax.set_axisbelow(True)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(COLORS["light_gray"])
    ax.spines["bottom"].set_color(COLORS["light_gray"])
    ax.tick_params(colors=COLORS["gray"], labelsize=MID, length=0, pad=2)

    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=4, frameon=False,
              fontsize=MID, handlelength=1.4, handletextpad=0.3, columnspacing=0.9, borderaxespad=0,
              labelcolor=COLORS["ink"])
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT / "nowcast-starts-backtest.png"
    fig.savefig(out_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    DELIVERABLE_FIGS.mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_FIGS / out_path.name).write_bytes(out_path.read_bytes())
    print(f"Wrote {out_path} (+ copy in {DELIVERABLE_FIGS})")


if __name__ == "__main__":
    main()
