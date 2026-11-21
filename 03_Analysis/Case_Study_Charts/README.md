# Homebuilder case-study visuals

Edit the CSV inputs in `03_Analysis/Case_Study_Charts/data/`, then run:

```bash
python3 03_Analysis/Case_Study_Charts/build_case_study_visuals.py
```

Requires Python 3.10+ and Matplotlib. The script writes these current visuals to `03_Analysis/Case_Study_Charts/outputs/`:

- `competitor-scale-price-margin.png`
- `supplier-cost-stack-land-control.png`
- `customer-luxury-vs-entry.png`

## Inputs and definitions

- `company_metrics.csv` transcribes closings, ASP, reported gross margin, owned lots, and optioned/controlled lots from the project 10-K comparison workbook. D.R. Horton is FY2026; peers are FY2025, and fiscal year-ends differ.
- `supplier_cost_mix.csv` transcribes the NAHB 2024 home-price composition summarized in the working research notes. Values are rounded; costs plus profit add to 99.9%.
- `mortgage_capture.csv` records the 10-K-reported mortgage capture measures and their definitions. Denominators differ; Toll Brothers' 43.4% is a dollar-value measure, while the other points are home-count or buyer measures.
- `luxury_vs_entry_revenue.csv` holds Builder 100 home revenue (2022–2026 editions) with each builder's segment (luxury / move_up / entry). The customer chart shows the latest-year change. `mortgage_capture.csv` is kept as reference data but no longer charted.
- `materials_vs_home_prices.csv` holds both series since Oct 2019 in long format (date, series, value).
- `cash_buyer_shares.csv` separates company-level cash-buyer shares from the U.S. Census 2023 new single-family home reference.

The supplier chart's right panel indexes the FRED construction-materials PPI (`WPUSI012011`, monthly, Dec 2019 = 100) and the FHFA all-transactions house price index (`USSTHPI`, quarterly, 2019 Q4 = 100, plotted mid-quarter). `materials_vs_home_prices.csv` is extracted from the xlsx files in `04_Source_Data/Macro_Rates_Prices_Costs/`; re-export it when those files are refreshed.

The first-iteration preview images remain in `03_Analysis/Case_Study_Charts/outputs/` under their earlier filenames. Use the three filenames above for the current design.
