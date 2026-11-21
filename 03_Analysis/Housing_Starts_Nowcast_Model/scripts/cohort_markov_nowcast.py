#!/usr/bin/env python3
"""Age-structured cohort (semi-Markov) simulation of the housing pipeline.

Each month, a cohort of permits is authorized. From then on a unit sits in one
of two pipeline stages -- "authorized, not started" (ANS) or "under
construction" (UC) -- and either advances (starts, or completes) or stays,
depending on how many months it has already spent in that stage. This script
represents each stage as a linear state-space system

    state[t] = A @ state[t-1] + inflow[t] * e0
    outflow[t] = c @ state[t]

where `state` holds the count of units at each age (months in stage), `A` is
a shift matrix with survival probabilities on its sub-diagonal (plus a
self-loop on an absorbing "age 13+" tail state), and `c` holds the per-age
hazard (exit) probabilities. This is exactly a discrete-time, age-structured
Markov chain -- "linear algebra" applied to the stage-timing distributions in
`data/stage_timing_inputs.csv`.

Two parallel pipelines are run -- single-family (1-unit) and multifamily
(2+ units) -- because their timing distributions differ sharply, then summed.

Segments and stage definitions, hazards, and all modeling choices are
documented inline and in research.md. This intentionally supersedes the
rolling-OLS benchmark in nowcast_starts.py for the purpose of nowcasting the
next month's total starts; it does not re-use that script's output.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OBS = DATA / "monthly_observations.csv"

# ---------------------------------------------------------------------------
# 1. Timing distributions: 2025 Census Survey of Construction shares, national,
#    transcribed into data/stage_timing_inputs.csv from the project's
#    Census_SOC_Pct_Distribution_Authorization_to_Start.xlsx / Census_SOC_Pct_Distribution_Start_to_Completion.xlsx / Census_SOC_Avg_Months_*.xlsx
#    workbooks ("04_Source_Data/Census_Construction_Stage_Timing/"). Values below are the
#    "1-unit total" and "2+ units total" rows; see research.md for caveats
#    (these are timing-given-eventual-exit distributions, not conversion
#    rates -- conversion is handled separately below as a trailing starts/permits ratio).
# ---------------------------------------------------------------------------

# Authorization -> start. Bins: prior/same month, 1, 2, 3, 4-plus months.
AUTH_TO_START_PMF = {
    "1-unit": np.array([0.37, 0.34, 0.12, 0.06, 0.11]),
    "multi": np.array([0.30, 0.29, 0.15, 0.06, 0.20]),
}
AUTH_TO_START_MEAN = {"1-unit": 1.4, "multi": 2.4}  # months, 2025 annual average

# Start -> completion. Bins: 1-3, 4-6, 7-9, 10-12, 13-plus months.
START_TO_COMP_PMF = {
    "1-unit": np.array([0.17, 0.42, 0.20, 0.09, 0.12]),
    "multi": np.array([0.01, 0.09, 0.15, 0.15, 0.60]),
}
START_TO_COMP_MEAN = {"1-unit": 7.4, "multi": 16.5}  # months, 2025 annual average
START_TO_COMP_BLOCK_WIDTHS = [3, 3, 3, 3]  # widths of the first four bins (months)

# Permit -> start conversion. The timing PMFs above are conditional on a unit
# eventually starting, so on their own they imply 100% conversion. In the data,
# multifamily starts run ~79% of multifamily permits (stable 0.78-0.82 since
# 2010; lapsed/abandoned/re-permitted projects), while single-family starts run
# ~103% of 1-unit permits (starts in non-permit-issuing areas). We scale each
# segment's permit inflow by a trailing ratio of starts to permits, using only
# months strictly before t so the backtest has no look-ahead.
CONVERSION_WINDOW = 36  # months
CONVERSION_MIN_HISTORY = 12  # months; before this, assume 1.0 (warm-up only)


def trailing_conversion(starts: pd.Series, permits: pd.Series) -> np.ndarray:
    """Ratio of summed starts to summed permits over the prior CONVERSION_WINDOW months (excl. t)."""
    s = starts.rolling(CONVERSION_WINDOW, min_periods=CONVERSION_MIN_HISTORY).sum().shift(1)
    p = permits.rolling(CONVERSION_WINDOW, min_periods=CONVERSION_MIN_HISTORY).sum().shift(1)
    return (s / p).fillna(1.0).to_numpy()


def block_hazards(pmf: np.ndarray, block_widths: list[int], mean_target: float) -> np.ndarray:
    """Convert a bucketed exit-age PMF into a per-month hazard array.

    `pmf` has one entry per bucket; all buckets but the last have a known
    width (in months) and get a constant within-bucket hazard that reproduces
    the bucket's share of mass given survival into it. The last bucket is
    open-ended ("N-plus months"); its hazard is solved in closed form so the
    full (bucket-approximated) distribution's mean matches `mean_target`,
    using the project's separate annual mean-duration tables. Returns an
    array of per-month hazards covering ages 0..(last finite age), followed
    by one more entry for the open-ended tail's constant hazard.
    """
    pmf = pmf / pmf.sum()
    hazards: list[float] = []
    survival = 1.0
    age = 0
    mean_so_far = 0.0
    for bucket_idx, width in enumerate(block_widths):
        mass = pmf[bucket_idx]
        # Constant hazard p over `width` months s.t. survival*(1-(1-p)**width) == mass
        p = 1.0 - (1.0 - mass / survival) ** (1.0 / width)
        for k in range(width):
            hazards.append(p)
            mean_so_far += survival * p * age
            survival *= 1.0 - p
            age += 1
    tail_mass = pmf[-1]
    # tail_mass should equal `survival` here (mass remaining); use `survival`
    # directly for numerical robustness.
    tail_mass = survival
    # Solve constant tail hazard h s.t. mean_so_far + tail_mass*(age + (1-h)/h) == mean_target
    residual = (mean_target - mean_so_far) / tail_mass - age
    residual = max(residual, 1e-6)  # guard against inconsistent inputs
    h_tail = 1.0 / (1.0 + residual)
    hazards.append(h_tail)
    return np.array(hazards)


class CohortStage:
    """One age-structured linear stage: ages 0..K-1 explicit, age K = "K-plus" tail."""

    def __init__(self, hazards: np.ndarray):
        self.hazards = hazards  # length K+1 (K finite ages + 1 tail)
        self.k = len(hazards) - 1
        self.state = np.zeros(self.k + 1)

    def step(self, inflow: float) -> float:
        # Timing convention: exits in month t come from units already in the stage at the
        # end of t-1, so a permit's first chance to start is the month after it is issued
        # (age-0 hazard = Census "prior/same month" share). Tested against same-month entry:
        # this fits the 24-month backtest and the Census ANS/UC stock levels better.
        prev = self.state
        new = np.zeros_like(prev)
        new[0] = inflow
        # survivors age by one state
        new[1:] = prev[: self.k] * (1.0 - self.hazards[: self.k])
        new[self.k] += prev[self.k] * (1.0 - self.hazards[self.k])
        outflow = float(np.dot(prev, self.hazards))
        self.state = new
        return outflow

    def stock(self) -> float:
        return float(self.state.sum())


def load_panel() -> pd.DataFrame:
    long = pd.read_csv(OBS, comment="#", parse_dates=["date"])
    return long.pivot(index="date", columns="series_id", values="value").sort_index()


def main() -> None:
    panel = load_panel()
    required = {"PERMIT", "PERMIT1", "HOUST", "HOUST1F", "AUTHNOTTSA", "UNDCONTSA"}
    missing = required.difference(panel.columns)
    if missing:
        raise SystemExit(f"Missing required series: {sorted(missing)}")

    history = panel.dropna(subset=["PERMIT", "PERMIT1"]).index
    start, end = history.min(), history.max()
    months = pd.date_range(start, end, freq="MS")

    p = panel.loc[months]
    raw_permits_1u = p["PERMIT1"] / 12.0
    raw_permits_multi = (p["PERMIT"] - p["PERMIT1"]) / 12.0
    conv = {
        "1-unit": trailing_conversion(p["HOUST1F"] / 12.0, raw_permits_1u),
        "multi": trailing_conversion((p["HOUST"] - p["HOUST1F"]) / 12.0, raw_permits_multi),
    }
    # Effective (conversion-adjusted) permit inflow into the authorized-not-started stage.
    permits_1u = raw_permits_1u.to_numpy() * conv["1-unit"]
    permits_multi = raw_permits_multi.to_numpy() * conv["multi"]

    stages = {}
    for seg, permits in (("1-unit", permits_1u), ("multi", permits_multi)):
        h1 = block_hazards(AUTH_TO_START_PMF[seg], [1, 1, 1, 1], AUTH_TO_START_MEAN[seg])
        h2 = block_hazards(START_TO_COMP_PMF[seg], START_TO_COMP_BLOCK_WIDTHS, START_TO_COMP_MEAN[seg])
        stages[seg] = {
            "ans": CohortStage(h1),
            "uc": CohortStage(h2),
            "permits": permits,
        }

    n = len(months)
    starts_model = np.zeros(n)
    starts_by_seg = {seg: np.zeros(n) for seg in stages}
    ans_stock = {seg: np.zeros(n) for seg in stages}
    uc_stock = {seg: np.zeros(n) for seg in stages}
    completions_model = np.zeros(n)

    for i in range(n):
        for seg, s in stages.items():
            starts_i = s["ans"].step(s["permits"][i])
            comp_i = s["uc"].step(starts_i)
            starts_by_seg[seg][i] = starts_i
            starts_model[i] += starts_i
            completions_model[i] += comp_i
            ans_stock[seg][i] = s["ans"].stock()
            uc_stock[seg][i] = s["uc"].stock()

    starts_model_saar = starts_model * 12.0
    completions_model_saar = completions_model * 12.0
    ans_stock_total = ans_stock["1-unit"] + ans_stock["multi"]
    uc_stock_total = uc_stock["1-unit"] + uc_stock["multi"]

    out = pd.DataFrame(
        {
            "date": months,
            "starts_model_saar_thousands": starts_model_saar,
            "starts_actual_saar_thousands": panel.loc[months, "HOUST"].to_numpy(),
            "completions_model_saar_thousands": completions_model_saar,
            "completions_actual_saar_thousands": panel.loc[months, "COMPUTSA"].to_numpy(),
            "ans_stock_model_thousands": ans_stock_total,
            "ans_stock_actual_thousands": panel.loc[months, "AUTHNOTTSA"].to_numpy(),
            "uc_stock_model_thousands": uc_stock_total,
            "uc_stock_actual_thousands": panel.loc[months, "UNDCONTSA"].to_numpy(),
        }
    ).set_index("date")

    with (DATA / "cohort_markov_simulation.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "# Age-structured cohort (semi-Markov) simulation of permits->ANS->starts->UC->completions.\n"
            "# See scripts/cohort_markov_nowcast.py and research.md for the model and caveats.\n"
        )
        out.to_csv(handle)

    # --- Validation window: stock-level scale check and recent-period backtest ---
    valid = out.dropna(subset=["ans_stock_actual_thousands", "uc_stock_actual_thousands"])
    recent = valid.tail(60)
    ans_ratio = (recent["ans_stock_model_thousands"] / recent["ans_stock_actual_thousands"]).mean()
    uc_ratio = (recent["uc_stock_model_thousands"] / recent["uc_stock_actual_thousands"]).mean()
    backtest = valid.tail(24)
    mae = (backtest["starts_model_saar_thousands"] - backtest["starts_actual_saar_thousands"]).abs().mean()
    corr = backtest["starts_model_saar_thousands"].corr(backtest["starts_actual_saar_thousands"])

    print("=== Stock-level scale check (ratio != 1 => residual mis-sizing after the permit->start conversion adjustment) ===")
    print(f"  Model ANS stock / actual AUTHNOTTSA, trailing 60mo avg ratio: {ans_ratio:.2f}")
    print(f"  Model UC stock / actual UNDCONTSA, trailing 60mo avg ratio:  {uc_ratio:.2f}")
    print()
    print(f"=== Permit->start conversion (trailing {CONVERSION_WINDOW}mo starts/permits, as of {end:%Y-%m}) ===")
    print(f"  1-unit: {conv['1-unit'][-1]:.3f}   multifamily: {conv['multi'][-1]:.3f}")
    print()
    print("=== Backtest: model-implied starts vs. actual HOUST, trailing 24 months ===")
    print(f"  MAE: {mae:.1f} thousand units SAAR")
    print(f"  Correlation: {corr:.2f}")
    print()

    # --- One-step-ahead nowcast for the first month after the observed sample ---
    # Same timing as CohortStage.step: next month's starts are the exits from everything
    # waiting at the end of the last observed month, so the nowcast uses only permits that
    # have already been reported -- no assumption about next month's permits is needed.
    next_month = end + pd.offsets.MonthBegin(1)
    by_seg = {seg: float(np.dot(s["ans"].state, s["ans"].hazards)) for seg, s in stages.items()}
    latest_cohort = {seg: float(s["ans"].state[0] * s["ans"].hazards[0]) for seg, s in stages.items()}
    nowcast_saar = sum(by_seg.values()) * 12.0
    latest_cohort_saar = sum(latest_cohort.values()) * 12.0
    older_backlog_saar = nowcast_saar - latest_cohort_saar

    actual_prior_month = float(panel.loc[end, "HOUST"])
    year_ago = next_month - pd.DateOffset(years=1)
    actual_year_ago = float(panel.loc[year_ago, "HOUST"]) if year_ago in panel.index else float("nan")

    print(f"=== Nowcast for {next_month:%Y-%m} total starts (SAAR, thousands) ===")
    print(f"  From permits issued in {end:%Y-%m} (newest cohort, first month eligible to start): {latest_cohort_saar:.0f}")
    print(f"  From older permits still waiting to start: {older_backlog_saar:.0f}")
    print(f"  By segment: 1-unit {by_seg['1-unit'] * 12:.0f}, 2+ units {by_seg['multi'] * 12:.0f}")
    print(f"  Total nowcast: {nowcast_saar:.0f}")
    print(f"  Actual {end:%Y-%m} (prior month): {actual_prior_month:.0f}  -> implied m/m change: {nowcast_saar - actual_prior_month:+.0f}")
    if not np.isnan(actual_year_ago):
        print(f"  Actual {year_ago:%Y-%m} (same month last year): {actual_year_ago:.0f}  -> implied y/y change: {nowcast_saar - actual_year_ago:+.0f} ({(nowcast_saar / actual_year_ago - 1) * 100:+.1f}%)")
    print()
    print("Interpretation: this is a methodology prototype. Hazards are calibrated only to 2025 national")
    print("annual timing shares/means plus a trailing permit->start conversion ratio (no region/structure-class granularity beyond")
    print("1-unit vs. 2+ units, no revision/vintage handling). See the stock-level scale check above before")
    print("treating the nowcast as more than a first-pass, model-consistent estimate.")


if __name__ == "__main__":
    main()
