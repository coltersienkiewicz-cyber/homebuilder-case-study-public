# Research note: a monthly housing-starts pipeline

## Question

Can observed permits and pipeline inventories improve a nowcast of monthly housing starts, and can cohort timing explain when permits convert into starts?

The useful conceptual distinction is between **flows** (permits issued, starts, completions during a month) and **stocks** (authorized-but-not-started and under-construction units at month end). A lagged relationship between aggregate permits and starts is a useful first benchmark, but it does not identify the fate or age of any particular permit cohort.

## Primary source and what it measures

The U.S. Census Bureau's New Residential Construction (NRC) release combines the Building Permits Survey and Survey of Construction. It reports permits, authorized-but-not-started units, starts, under-construction units, and completions. The Census methodology notes that some permitted projects are abandoned before starting, and some started projects are abandoned before completion. Thus these stages are not a closed conveyor belt with perfect conversion.

Source pages:

1. [Census New Residential Construction overview](https://www.census.gov/construction/nrc/index.html) — definitions, coverage, and links to data.
2. [Census historical time series](https://www.census.gov/construction/nrc/data/series.html) — historical monthly/annual tables.
3. [Census length-of-time tables](https://www.census.gov/construction/nrc/data/time.html) — annual duration distributions from authorization to start and start to completion.
4. [Census starts-rate tables](https://www.census.gov/construction/nrc/starts_rates.html) — ratios of starts in a given month to permits issued in the authorization month, with regional and division detail. This is especially useful for direct cohort conversion calibration.
5. [Census Survey of Construction methodology](https://www.census.gov/construction/soc/methodology.html) — sample, estimates, and revisions.
6. [Census NRC relationships note](https://www.census.gov/construction/pdf/nrc_relationships.pdf) — coverage and relationships among survey stages.

FRED republishes Census/HUD monthly series and is the convenient machine-readable source. The editable observations currently included were transcribed from the uploaded `04_Source_Data/FRED_Housing_Pipeline/FRED_Housing_Pipeline_Starts_Permits_UnderConstr_Completions_AuthNotStarted_1959-2026.csv`, with comments preserving its source and unit conventions. The series catalog records each ID and convention. To refresh/extend, run `scripts/fetch_fred.py`.

## Initial series

| Stage / measure | Series ID | Role | Convention |
|---|---|---|---|
| Permits, total | `PERMIT` | Monthly permit flow | Thousands, SAAR |
| Starts, total | `HOUST` | Target monthly starts flow | Thousands, SAAR |
| Under construction, total | `UNDCONTSA` | Pipeline inventory | Thousands, seasonally adjusted stock |
| Authorized, not started, total | `AUTHNOTTSA` | Permit backlog inventory | Thousands, seasonally adjusted stock |

Additional IDs are listed in `data/series_catalog.csv`, including the corresponding single-family series and completions. The user can extend that file and `SERIES` in `scripts/fetch_fred.py` when adding data. Census table downloads are the preferred source for starts-by-authorization-month and regional cohort detail.

## Modeling proposal

### Current implementation status

The current `scripts/nowcast_starts.py` is an aggregate rolling OLS benchmark. It does **not** yet create permit-month cohorts or estimate type-by-region conversion probabilities. The uploaded `04_Source_Data/FRED_Housing_Pipeline/FRED_Housing_Pipeline_Starts_Permits_UnderConstr_Completions_AuthNotStarted_1959-2026.csv` is a wide national panel with five series, not a type-by-region panel. Its permits, starts, under-construction, and completions series are monthly SAAR flows; `AUTHNOTTSA` is an adjusted inventory stock.

The four workbooks in `04_Source_Data/Census_Construction_Stage_Timing/` provide Census Survey of Construction timing inputs, normalized in `data/stage_timing_inputs.csv`. The 2025 percent distributions separate U.S., Northeast, Midwest, South, and West, with structure classes including 1 unit, 2–4, 5–9, 10–19, and 20+. Authorization-to-start distributions use lag bins `prior to or same month`, `1`, `2`, `3`, and `4+`; start-to-completion distributions use `3 months or less`, `4–6`, `7–9`, `10–12`, and `13+`. The companion annual average-duration workbooks are separate summary measures. Preserve these bins and the original detailed structure classes until valid aggregation weights are available.

These timing distributions describe the timing of buildings that started/completed, conditional on the observed stage exit. They are not, by themselves, the probability that a permit will ever convert to a start. The mean duration does not supply the missing conversion share either. Use Census starts-rate tables (started units from each authorization-month cohort divided by units permitted in that cohort) to estimate conversion and cohort-age behavior, then use the duration tables as smoothing/shape information where rates are sparse. A backtest must use only starts-rate information published by each forecast date.

The monthly `newresconst.pdf` release provides recent monthly detail for the U.S. by 1-unit, 2–4-unit, and 5+-unit groups, but its regional tables report total and 1-unit detail. It is not a complete historical permit-month × structure-type × region cohort input. For the requested panel, collect historical monthly permit units by region and size class from Census BPS/NRC tables or explicitly model an allocation for the missing cross-breaks. Do not describe an allocated split as observed data.

The target cohort table should have one row per `permit_month × region × structure_type`, with `permits_units` in monthly units and provenance. Use the three analysis groups `1-unit`, `2–4-unit`, and `5+-unit`, retaining source subgroups for 5–9, 10–19, and 20+ where possible. For lag `a`, estimate a cohort start contribution as:

`expected_starts[t, g, r] = Σ_a permits[t-a, g, r] × conversion[g, r] × timing_share[a, g, r]`

where `conversion` is anchored to observed cohort start rates and `timing_share` is normalized over age. Since Census timing tables place all starts at 4+ months in one bin, either keep an explicit 4+ tail state or estimate its age distribution using the annual duration statistics; do not silently treat the entire bin as exactly month 4. Sum segment predictions for the total starts nowcast and compare both segment and aggregate predictions with observed starts.

### 1. Start with a transparent nowcast benchmark

For total starts, estimate a monthly dynamic regression/state-space benchmark with lagged starts, contemporaneous permits, and observed inventories (authorized-not-started and under-construction). Include month-of-year effects when working with NSA flows; seasonally adjusted data are simpler for the first pass. Use rolling-origin evaluation and compare against a seasonal-naive and autoregressive benchmark. Current-month predictor availability must mirror the real publication calendar.

### 2. Use cohort data to estimate conversion, not just aggregate correlations

The most informative direct source is the Census starts-rate table: permit-month cohorts are followed to determine how much starts in a later month came from permits issued in each authorization month. Represent it as a lower-triangular matrix `C[a, t]`, where `a` is permit age in months and `t` is the observation month, and each cell is starts from the cohort at that age. Normalize by permits issued for that cohort to estimate age-specific conversion hazards. Separate starts in permit-issuing and non-permit-issuing areas as the source tables permit.

For richer micro-style cohorts, define stage-state rows such as `authorized_not_started(age)`, `under_construction(age)`, and `completed(age)` and estimate monthly transition/exit probabilities. A cohort may stay in the stage, advance, or exit through cancellation/abandonment. Census duration distributions constrain the transition timing. Aggregate monthly stocks alone cannot recover full cohort ages; use the direct starts-rate/duration tables for identification and treat model-derived cohort allocations as latent estimates.

### 3. Use inventory accounting as a diagnostic, not an identity without qualifications

For authorized-not-started inventory, a rough balance is:

`ending backlog = beginning backlog + permits entering backlog - starts sourced from backlog - cancellations/revisions`

This helps interpret the backlog as a leading indicator, but permits and starts coverage can differ (including non-permit-issuing areas), and revisions/cancellations mean the equality will not close perfectly. Under-construction inventory similarly reflects starts entering and completions/abandonments leaving.

### 4. Expand in layers

1. National total baseline.
2. Single-family versus 2–4 and 5+ unit groups.
3. Census regions/divisions.
4. Age-specific cohort transition rates and duration distributions.
5. Publication-vintage-aware evaluation and revision analysis.

Avoid fitting all type-region-age transitions at once: sample sizes and aggregate data limitations make that unstable. Pool or regularize rates across related cohorts, then add segment detail if out-of-sample results improve.

## Units, timing, and caveats

- SAAR is an annualized rate. Divide an SAAR flow by 12 to obtain a monthly-equivalent flow before comparing it with inventories measured in thousands of units. For cohort shares, use consistent seasonal-adjustment conventions or use Census NSA cohort tables.
- Stocks are point-in-time inventories and should not be divided by 12.
- The uploaded panel uses seasonally adjusted flow rates and adjusted pipeline stocks. The series history begins at different dates, so matched model sample coverage is determined by the latest-starting feature.
- Census monthly releases revise recent months and seasonal factors. A genuine historical nowcast test needs archived releases/ALFRED vintages; latest-vintage history can overstate real-time performance.
- The permit-to-start lag is not a single fixed duration. Abandonment and starts in non-permit areas break a naïve one-to-one conversion assumption.
- The five-series panel has differing history lengths; the matched model sample begins when the last required predictor, authorized-not-started inventory, becomes available in 1999. Lags shorten the estimation sample further. Keep the exact sample and latest-vintage/revision caveat with any reported score.

## Next data to add

1. Census starts-rate tables by authorization month (national and region/division; ideally single-family and multifamily), which directly inform cohort conversion.
2. Historical monthly permit cohort counts by region and the requested type groups (or source components sufficient to derive them).
3. Census starts-rate tables with authorization month, observation/start month, region, and unit-size class; store each release vintage.
4. Census annual length-of-time distributions and means by the same strata, with source subgroup classes retained.
5. Full monthly history for permits, starts, inventories, and completions with consistent seasonal-adjustment and geographic scope.
6. Archived vintages for pseudo-real-time backtests.

## Cohort-Markov model: permit->start conversion (added 2026-11-20)

`scripts/cohort_markov_nowcast.py` originally implied 100% permit->start conversion (the SOC timing PMFs are conditional on an eventual start), which biased modeled starts ~+78k SAAR over the 24-month backtest (above actual in ~85% of months). Segment ratios of starts to permits are stable: multifamily ~0.79 (0.78-0.82 since 2010), single-family ~1.03 (non-permit-area starts). The model now scales each segment's permit inflow by a trailing 36-month starts/permits ratio computed only from months before t (no look-ahead). Result: 24-month bias ~-9k, MAE 90k -> 62k. Residual stock mismatch: ANS 1.16x AUTHNOTTSA, UC 0.90x UNDCONTSA (the earlier ~1.02 UC fit was offsetting errors). A cohort-based conversion from Census starts-rate tables would be the cleaner replacement.

## Notes for the brief: why monthly starts are noisy (added 2026-11-20)

These points explain why the cohort model's monthly miss (24-month MAE 62k SAAR, correlation 0.45) is not all model error. The model is unchanged; these are caveats and framing for the write-up.

1. **Survey sampling error.** Census estimates monthly starts from a sample of permit offices, not a full count, and publishes a 90% confidence interval with every release. For the month-over-month change in total starts that interval is typically about ±10-14%, roughly ±130-180k SAAR at current levels. Examples: Jan 2026 +7.2% (±13.7%), Aug 2026 -2.6% (±12.0%); neither was statistically significant. A single monthly miss smaller than the Census's own error band can't be separated from noise. Sources: Census NRC releases ([Jan 2026](https://www.census.gov/construction/nrc/pdf/newresconst_202601.pdf), [Aug 2026](https://www.census.gov/construction/nrc/pdf/newresconst_202608.pdf), [Sep 2026](https://www.census.gov/construction/nrc/pdf/newresconst_202609.pdf)); [NRC release FAQs](https://census.gov/construction/pdf/nrc_release_faqs.pdf).
2. **Lumpy multifamily starts.** One apartment building can add hundreds of units in a single month. In our data (FRED HOUST, HOUST1F; Nov 2022-Oct 2026), multifamily (2+ units) averages about 426k SAAR, about 31% of starts, but its month-to-month change has a standard deviation of about 92k vs. about 69k for single-family. Multifamily accounts for about 58% of the month-to-month variance in total starts. Single-family, the segment most relevant to public homebuilders, is the steadier series. Sources: own calculation from FRED; [NMHC](https://nmhc.org/news/articles/a-closer-look-at-monthly-starts-figures); [RealPage](https://www.realpage.com/analytics/multifamily-starts-unlikely-spiking/).
3. **Weather and timing.** Unusual cold, rain or hurricanes shift starts between months. Seasonal adjustment removes the normal winter slowdown but not an abnormal month. Permits are much less weather-sensitive (month-to-month standard deviation about 71k vs. 121k for starts over the same window). Sources: [PCBB](https://www.pcbb.com/industry-insights/economy/2017-05-16-housing-starts); [Haver Analytics](https://www.haver.com/articles/u-s-housing-starts-fell-markedly-in-january-after-december-surge).
4. **Revisions.** First prints are revised in the next two releases, and seasonal factors are revised annually. The backtest compares against latest-vintage data, so a real-time test (ALFRED vintages) would look somewhat different. See "Units, timing, and caveats" above. Source: [NMHC](https://nmhc.org/news/articles/a-closer-look-at-monthly-starts-figures).

**Implication for reading the backtest.** The model is built to track the underlying trend in starts. Against a 3-month moving average of actual starts, the same model line over the same 24 months (Nov 2024-Oct 2026) has an MAE of 31k (vs. 62k against single months) and a correlation of 0.64 (vs. 0.45). Most of the remaining monthly miss is within the range of Census sampling error and multifamily lumpiness, not a signal the model is missing. The November 2026 nowcast (1,299k, ± 62k backtest MAE) should be read as a trend-level estimate. On a single month, a print anywhere from about 1,200k to 1,400k would be consistent with it.

Suggested one-line chart caption: "Monthly starts carry ±10-14% Census sampling error and lumpy multifamily starts; the model targets the trend (3-month-average MAE 31k)."

## Timing convention (fixed 2026-11-21)

The simulation lets a permit's first chance to start come in the month *after* it is issued (the age-0 hazard is applied the following month). The original one-step-ahead nowcast used a different convention: it dropped the newest (already-reported) permit cohort and replaced it with an assumed next-month permit count (trailing 3-month average) starting in the same month. The two are now consistent: the nowcast is the exits from everything waiting at the end of the last observed month, so it uses only reported permits.

Same-month starts were also tested for both the simulation and the nowcast. That version fit worse: 24-month MAE of 65.8k vs. 62.4k, correlation 0.35 vs. 0.45, and modeled ANS/UC stocks at 0.73/0.82 of Census vs. 1.16/0.90. The next-month convention was kept.

Effect on the November 2026 nowcast: 1,299k → 1,274k (418k from October permits + 856k from older permits). Backtest statistics are unchanged.
