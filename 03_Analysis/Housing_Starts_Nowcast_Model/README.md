# Housing pipeline nowcast

This folder contains a first working structure for studying monthly housing starts as a pipeline process.

## Files

- `research.md` documents the data sources, definitions, and modeling decisions.
- `data/monthly_observations.csv` is the editable long-format source data panel. Lines beginning with `#` are provenance notes; the Python scripts skip them.
- `data/series_catalog.csv` lists series IDs and units/adjustment conventions.
- `scripts/fetch_fred.py` downloads selected FRED series as CSV.
- `scripts/build_cohorts.py` prepares lags, stock-flow checks, and an illustrative cohort-lag feature table.
- `scripts/nowcast_starts.py` fits a baseline monthly model using only information available through the prior month. It is a prototype, not a validated forecast.
- `scripts/cohort_markov_nowcast.py` is the main nowcast: an age-structured (semi-Markov) cohort simulation of permits -> not started -> starts -> under construction -> completions, split single-family vs. 2+ units. Permit inflow is scaled by a trailing 36-month starts/permits ratio per segment (no look-ahead), since the Census timing tables alone imply 100% conversion. Writes `data/cohort_markov_simulation.csv`.
- `scripts/plot_nowcast_chart.py` re-runs the cohort model and writes `03_Analysis/Case_Study_Charts/outputs/nowcast-starts-backtest.png` for the write-up.
- `scripts/extract_timing_inputs.py` normalizes the provided Census duration workbooks into `data/stage_timing_inputs.csv`.

Run from the project root:

```bash
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/fetch_fred.py
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/build_cohorts.py
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/nowcast_starts.py
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/plot_nowcast_chart.py
```

`fetch_fred.py` needs network access. It replaces/refreshes the observations in the input panel for the configured series while preserving the provenance comment block. If adding your own observations, retain the columns `date,series_id,value` and add a source note in the CSV comments or `research.md`.

## First-pass scope

The editable observations now come from the uploaded `04_Source_Data/FRED_Housing_Pipeline/FRED_Housing_Pipeline_Starts_Permits_UnderConstr_Completions_AuthNotStarted_1959-2026.csv`. It has five national series with differing availability: starts from Jan 1959, permits from Jan 1960, under-construction from Jan 1970, completions from Jan 1968, and seasonally adjusted authorized-not-started inventory from Jan 1999. The baseline is national and aggregate. The OLS baseline deliberately leaves housing type, region, cohort-specific conversion, and survey vintage/revisions as extensions.

SAAR flows and stocks must not be treated as the same unit. The modeling script converts SAAR flow series to monthly-equivalent units by dividing by 12; inventory series stay as stocks. The initial source workbook has mixed adjustment conventions, so the scripts keep `series_id` and consult the catalog rather than assuming the same units for every column.
