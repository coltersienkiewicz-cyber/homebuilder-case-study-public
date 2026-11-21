#!/usr/bin/env python3
"""Simple one-month-ahead starts benchmark with expanding-window evaluation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "monthly_observations.csv"
FEATURES = ["starts_lag1", "permits_lag1", "permits_lag2", "backlog_lag1", "under_construction_lag1"]
MIN_TRAIN = 24


def main() -> None:
    long = pd.read_csv(INPUT, comment="#", parse_dates=["date"])
    panel = long.pivot(index="date", columns="series_id", values="value").sort_index()
    required = {"HOUST", "PERMIT", "AUTHNOTTSA", "UNDCONTSA"}
    missing = required.difference(panel.columns)
    if missing:
        raise SystemExit(f"Missing required series: {', '.join(sorted(missing))}")

    # Predict t from t-1 values to avoid using not-yet-published month-t predictors.
    design = pd.DataFrame(index=panel.index)
    design["target"] = panel["HOUST"] / 12.0
    design["starts_lag1"] = design["target"].shift(1)
    design["permits_lag1"] = (panel["PERMIT"] / 12.0).shift(1)
    design["permits_lag2"] = (panel["PERMIT"] / 12.0).shift(2)
    design["backlog_lag1"] = panel["AUTHNOTTSA"].shift(1)
    design["under_construction_lag1"] = panel["UNDCONTSA"].shift(1)
    fit_data = design.dropna()

    predictions = []
    for i in range(MIN_TRAIN, len(fit_data)):
        train = fit_data.iloc[:i]
        test = fit_data.iloc[[i]]
        x_train = np.column_stack([np.ones(len(train)), train[FEATURES].to_numpy(dtype=float)])
        x_test = np.r_[1.0, test[FEATURES].to_numpy(dtype=float)[0]]
        coef, *_ = np.linalg.lstsq(x_train, train["target"].to_numpy(dtype=float), rcond=None)
        predictions.append((test.index[0], float(test["target"].iloc[0]), float(x_test @ coef)))

    output = pd.DataFrame(predictions, columns=["date", "actual_starts_monthly_equiv_thousands", "predicted_starts_monthly_equiv_thousands"])
    with (DATA / "rolling_nowcast.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("# Derived from monthly_observations.csv; estimates use an expanding-window OLS baseline. See research.md.\n")
        output.to_csv(handle, index=False)
    if len(output):
        mae = (output["actual_starts_monthly_equiv_thousands"] - output["predicted_starts_monthly_equiv_thousands"]).abs().mean()
        # Latest nowcast uses the most recent predictor month to forecast the next month.
        train = fit_data
        x_train = np.column_stack([np.ones(len(train)), train[FEATURES].to_numpy(dtype=float)])
        coef, *_ = np.linalg.lstsq(x_train, train["target"].to_numpy(dtype=float), rcond=None)
        latest = panel.dropna(subset=list(required)).index.max()
        next_month = latest + pd.offsets.MonthBegin(1)
        last_row = design.loc[latest, FEATURES].to_numpy(dtype=float)
        estimate = float(np.r_[1.0, last_row] @ coef)
        print(f"Rolling-origin MAE: {mae:.2f} thousand units/month equivalent")
        print(f"Next-month prototype nowcast ({next_month:%Y-%m}): {estimate:.2f} thousand units/month equivalent")
        print("Interpret as a baseline only; latest-vintage data and release timing are not modeled.")
    else:
        print("Not enough history for the configured expanding-window evaluation.")


if __name__ == "__main__":
    main()
