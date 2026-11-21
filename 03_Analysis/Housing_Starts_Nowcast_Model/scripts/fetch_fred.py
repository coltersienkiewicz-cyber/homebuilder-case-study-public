#!/usr/bin/env python3
"""Fetch configured FRED series and write a long-format editable CSV.

Requires pandas. FRED's graph CSV endpoint does not require an API key.
"""
from __future__ import annotations

import csv
import ssl
from datetime import date
from io import StringIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd
import certifi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "monthly_observations.csv"
CATALOG = ROOT / "data" / "series_catalog.csv"
SERIES = pd.read_csv(CATALOG, comment="#")["series_id"].dropna().astype(str).tolist()
BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="


def main() -> None:
    tls_context = ssl.create_default_context(cafile=certifi.where())
    rows = []
    available = []
    unavailable = []
    for series_id in SERIES:
        try:
            with urlopen(BASE_URL + series_id, timeout=60, context=tls_context) as response:
                raw = response.read().decode("utf-8-sig")
        except HTTPError as exc:
            if exc.code == 404:
                unavailable.append(series_id)
                continue
            raise SystemExit(f"FRED request failed for {series_id}: HTTP {exc.code}") from exc
        available.append(series_id)
        frame = pd.read_csv(StringIO(raw), na_values=["."])
        date_column = frame.columns[0]
        value_column = frame.columns[1]
        for _, row in frame.iterrows():
            if pd.notna(row[value_column]):
                rows.append((pd.to_datetime(row[date_column]).strftime("%Y-%m-%d"), series_id, float(row[value_column])))

    note = [
        "# Source: FRED graph CSV endpoint; underlying source U.S. Census Bureau and U.S. Department of Housing and Urban Development.",
        f"# Retrieved: {date.today().isoformat()}",
        f"# Retrieved series IDs: {', '.join(available)}. See ../research.md and series_catalog.csv for definitions.",
    ]
    if unavailable:
        note.append(f"# FRED returned HTTP 404 for these catalog IDs: {', '.join(unavailable)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        handle.write("\n".join(note) + "\n")
        writer = csv.writer(handle)
        writer.writerow(["date", "series_id", "value"])
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} observations to {OUT}")


if __name__ == "__main__":
    main()
