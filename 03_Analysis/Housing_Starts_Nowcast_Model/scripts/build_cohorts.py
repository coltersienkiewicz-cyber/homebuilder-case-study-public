#!/usr/bin/env python3
"""Create lag features and stock-flow diagnostic tables from the source CSV."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "monthly_observations.csv"


def load_panel() -> pd.DataFrame:
    long = pd.read_csv(INPUT, comment="#", parse_dates=["date"])
    wide = long.pivot(index="date", columns="series_id", values="value").sort_index()
    wide.index.name = "date"
    return wide


def write_with_source(frame: pd.DataFrame, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# Derived from monthly_observations.csv; source definitions and provenance are in research.md and series_catalog.csv.\n")
        frame.to_csv(handle, na_rep="")


def main() -> None:
    panel = load_panel()
    # SAAR flow series become monthly-equivalent thousands of units. Stocks remain stocks.
    for series_id in ("PERMIT", "HOUST"):
        if series_id in panel:
            panel[f"{series_id}_monthly_equiv"] = panel[series_id] / 12.0

    features = pd.DataFrame(index=panel.index)
    features["starts_monthly_equiv"] = panel.get("HOUST", pd.Series(index=panel.index, dtype=float)) / 12.0
    # Lagged total permits are a proxy for cohort inflow; the Census starts-rate tables
    # should replace these aggregate proxies when authorization-month cohort data is added.
    if "PERMIT" in panel:
        permits = panel["PERMIT"] / 12.0
        for age in range(0, 13):
            features[f"permit_lag_{age}m_monthly_equiv"] = permits.shift(age)
    for series_id in ("AUTHNOTTSA", "UNDCONTSA"):
        if series_id in panel:
            features[f"{series_id}_stock"] = panel[series_id]
            features[f"{series_id}_change"] = panel[series_id].diff()
    features.index.name = "date"
    write_with_source(features, DATA / "lag_features.csv")

    # This diagnostic is intentionally approximate: scopes and revisions can differ.
    if {"AUTHNOTTSA", "PERMIT", "HOUST"}.issubset(panel.columns):
        diag = pd.DataFrame(index=panel.index)
        diag["authorized_not_started_stock"] = panel["AUTHNOTTSA"]
        diag["permit_flow_monthly_equiv"] = panel["PERMIT"] / 12.0
        diag["starts_flow_monthly_equiv"] = panel["HOUST"] / 12.0
        diag["backlog_change"] = panel["AUTHNOTTSA"].diff()
        diag["rough_unexplained_change"] = (
            diag["backlog_change"] - diag["permit_flow_monthly_equiv"] + diag["starts_flow_monthly_equiv"]
        )
        diag.index.name = "date"
        write_with_source(diag, DATA / "stock_flow_diagnostic.csv")

    print(f"Wrote feature and diagnostic tables for {len(panel)} months to {DATA}")


if __name__ == "__main__":
    main()
