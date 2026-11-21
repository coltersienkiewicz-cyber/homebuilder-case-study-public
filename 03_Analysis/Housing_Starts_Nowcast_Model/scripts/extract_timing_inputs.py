#!/usr/bin/env python3
"""Normalize Census pipeline timing workbooks into one editable long CSV."""
from __future__ import annotations

import csv
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]  # project root (ROOT is 03_Analysis/Housing_Starts_Nowcast_Model)
SOURCE = PROJECT / "04_Source_Data" / "Census_Construction_Stage_Timing"
OUT = ROOT / "data" / "stage_timing_inputs.csv"

STRUCTURE_CLASSES = [
    "1-unit total",
    "1-unit built-for-sale",
    "1-unit contractor-built",
    "1-unit owner-built",
    "2+ units total",
    "2-4 units",
    "5-9 units",
    "10-19 units",
    "20+ units",
]
LAG_BUCKETS = {
    "prior to or same month": "prior_or_same_month",
    "prior to or same month as authorization": "prior_or_same_month",
    "1 month": "1_month",
    "2 months": "2_months",
    "3 months": "3_months",
    "4 months or more": "4_plus_months",
    "3 months or less": "3_or_less_months",
    "4 to 6 months": "4_to_6_months",
    "7 to 9 months": "7_to_9_months",
    "10 to 12 months": "10_to_12_months",
    "13 months or more": "13_plus_months",
}


def open_sheet(path: Path, sheet_name: str | None = None):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return workbook[ sheet_name or workbook.sheetnames[0] ]


def distribution_rows(path: Path, phase: str) -> list[list[object]]:
    ws = open_sheet(path)
    rows = list(ws.values)
    year = int(rows[3][0])
    records: list[list[object]] = []
    geography = None
    measure = "percent_distribution"
    regions = {"United States", "Northeast", "Midwest", "South", "West"}
    for row in rows[7:]:
        label = row[0]
        if label == "Relative Standard Error":
            measure = "relative_standard_error_pct"
            geography = None
            continue
        if label == "Footnotes:":
            break
        if isinstance(label, str) and label in regions:
            geography = label
            continue
        if geography and isinstance(label, str) and label.strip().lower() in LAG_BUCKETS:
            for col_idx, structure in enumerate(STRUCTURE_CLASSES, start=1):
                value = row[col_idx]
                records.append([
                    phase, measure, year, geography, structure,
                    LAG_BUCKETS[label.strip().lower()], value, "percent", path.name,
                ])
    return records


def mean_duration_rows(path: Path, phase: str) -> list[list[object]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records: list[list[object]] = []
    for geography in workbook.sheetnames:
        rows = list(workbook[geography].values)
        for row in rows[6:]:
            year = row[0]
            if not isinstance(year, (int, str)) or not str(year).isdigit():
                continue
            for col_idx, structure in enumerate(STRUCTURE_CLASSES, start=1):
                value = row[col_idx]
                if value is not None:
                    records.append([
                        phase, "mean_duration", int(year), geography, structure,
                        "", value, "months", path.name,
                    ])
    return records


def main() -> None:
    records = []
    records += distribution_rows(SOURCE / "Census_SOC_Pct_Distribution_Authorization_to_Start.xlsx", "authorization_to_start")
    records += distribution_rows(SOURCE / "Census_SOC_Pct_Distribution_Start_to_Completion.xlsx", "start_to_completion")
    records += mean_duration_rows(SOURCE / "Census_SOC_Avg_Months_Authorization_to_Start.xlsx", "authorization_to_start")
    records += mean_duration_rows(SOURCE / "Census_SOC_Avg_Months_Start_to_Completion.xlsx", "start_to_completion")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        handle.write("# Source: Census Survey of Construction timing workbooks in project folder 04_Source_Data/Census_Construction_Stage_Timing/.\n")
        handle.write("# Percent distributions are 2025 shares; durations retain annual values from each workbook. Timing units/classes are structure-level as labeled by Census.\n")
        handle.write("# See research.md for use, conversion caveats, and source links.\n")
        writer = csv.writer(handle)
        writer.writerow([
            "phase", "statistic", "year", "geography", "structure_class",
            "lag_bucket", "value", "value_units", "source_file",
        ])
        writer.writerows(records)
    print(f"Wrote {len(records):,} timing observations to {OUT}")


if __name__ == "__main__":
    main()
