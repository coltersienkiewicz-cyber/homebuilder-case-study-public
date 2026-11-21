# Point72 MI Data — Data Research Case Study: U.S. Homebuilder Industry

> **Public version.** The original assignment brief and the pre-cleanup copies of the research notes are not included. Folder numbering is unchanged, so `02_` is absent.

This folder holds everything behind my case study: the deliverable, the brief, the analysis code and workbooks, the public source data, and my research notes and AI chat logs.

**The case study answers four questions**:
1. Who are the homebuilder industry's customers, competitors and suppliers?
2. Which KPIs matter most, and what drives them?
3. Which public data gives insight into those KPIs, and why?
4. A nowcast of the next unreleased Census "New Privately-Owned Housing Units Started: Total Units" print, compared with the prior month and the same month last year.

## Where to start

| If you want to… | Open |
|---|---|
| Read the finished write-up | `01_Final_Deliverable/MI_Data_Case_Study_Draft_Compiled_2026-11-21.pdf` |
| Check the company numbers | `03_Analysis/Excel_Workbooks/` |
| Understand the housing-starts nowcast | `03_Analysis/Housing_Starts_Nowcast_Model/README.md`, then `research.md` |
| See how the charts are built | `03_Analysis/Case_Study_Charts/README.md` |
| Trace a figure back to its source | `04_Source_Data/` (raw public files), then the citations in the deliverable |
| See how the research developed, and how AI was used | `05_Research_Notes_and_AI_Chat_Logs/` (read files 01 → 05 in order) |

## How the pieces connect

```
04_Source_Data  ──►  03_Analysis  ──►  01_Final_Deliverable
(10-Ks, Census,      (Excel workbooks,   (LaTeX source + compiled PDF;
 FRED, BLS, FHFA,     chart scripts,      charts pulled from
 NAHB, Google         nowcast model)      03_Analysis/Case_Study_Charts/outputs/)
 Trends)
        ▲
05_Research_Notes_and_AI_Chat_Logs — the planning and Q&A that shaped what was pulled and built
```

## Folder guide

### `01_Final_Deliverable/`
| File | What it is |
|---|---|
| `MI_Data_Case_Study_Main.tex` | LaTeX source for the case study body (sections 1–5). Compile this file. |
| `MI_Data_Case_Study_Sources_and_AI_Disclosure.tex` | Numbered source list and the AI-use disclosure. Pulled into the main file via `\input`; keep both files in the same folder. |
| `MI_Data_Case_Study_Draft_Compiled_2026-11-21.pdf` | Compiled PDF of the current draft. |

To compile locally, run `pdflatex MI_Data_Case_Study_Main.tex` from inside `01_Final_Deliverable/`. The images are found automatically in `03_Analysis/Case_Study_Charts/outputs/` via `\graphicspath`. On Overleaf, upload both `.tex` files plus the four PNGs from that folder.

### `03_Analysis/`
| Item | What it is |
|---|---|
| `Excel_Workbooks/10-K_Builder_KPI_Comparison_FY2025-26.xlsx` | Side-by-side KPIs for 10 public builders pulled from their 10-Ks (closings, ASP, gross margin, lots owned/optioned, etc.). |
| `Excel_Workbooks/Builder_100_Rankings_and_Trends_2022-2026.xlsx` | Builder 100 rankings for 2022–2026: a summary/trends tab, a master comparison tab, and one tab per year. |
| `Case_Study_Charts/` | Python script and CSV inputs that draw the industry-map charts (competitors, suppliers, customers). Final PNGs are in `outputs/`; superseded drafts are in `outputs/earlier_iterations/`. |
| `Housing_Starts_Nowcast_Model/` | The housing-starts nowcast: a cohort (semi-Markov) pipeline model of permits → not started → started → under construction → completed, plus a rolling OLS benchmark and a backtest. `research.md` documents the method and data decisions. |
| `Interactive_Supply_Demand_Simulator/` | An exploratory HTML supply/demand simulator for new housing (open it in a browser). |

**Reproduce the outputs** (run from the project root; needs Python 3.10+):

```bash
pip install -r requirements.txt
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/extract_timing_inputs.py   # Census timing workbooks -> stage_timing_inputs.csv
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/plot_nowcast_chart.py      # runs the nowcast + draws the backtest chart
python3 03_Analysis/Case_Study_Charts/build_case_study_visuals.py                   # draws the three industry-map charts
python3 03_Analysis/Housing_Starts_Nowcast_Model/scripts/fetch_fred.py              # optional: refresh FRED data (needs internet)
```

### `04_Source_Data/` (raw public data, unmodified)
| Folder | Contents |
|---|---|
| `Company_10-K_Filings/` | 10-Ks for D.R. Horton (FY ended Sep 2026), Lennar and KB Home (Nov 2025), Toll Brothers (Oct 2025), and PulteGroup, NVR, Meritage, Taylor Morrison, Century Communities and Sekisui House U.S. (Dec 2025). `Extracted_Text/` has plain-text copies so they can be searched. |
| `Census_New_Residential_Construction/` | The Census New Residential Construction release for October 2026 (published Nov 18, 2026), and a June 2024 Census article on median price per square foot by region. |
| `Census_Construction_Stage_Timing/` | Census Survey of Construction tables: average months, and the percent distribution, from permit to start and from start to completion. These are the inputs to the nowcast's lag structure. |
| `FRED_Housing_Pipeline/` | Monthly national housing starts (HOUST), permits (PERMIT), under construction (UNDCONTSA), completions (COMPUTSA) and authorized-not-started (AUTHNOTTSA), from FRED. |
| `Macro_Rates_Prices_Costs/` | Freddie Mac 30-year mortgage rate (MORTGAGE30US), FHFA house price index (USSTHPI), BLS construction-materials PPI (WPUSI012011), and NAHB's *Cost of Constructing a Home 2024* study. |
| `Google_Trends/` | Monthly U.S. Google Trends interest, Nov 2021–Nov 2026: one file of housing-market search terms (mortgage rates, building permits, new home construction…) and one of big-city permit-office searches. |

### `05_Research_Notes_and_AI_Chat_Logs/`
Research notes and exported AI chats, in the order they were used. Files 01–04 were cleaned up and re-formatted for readability: headings and tables were added, ASCII and SVG diagrams were rebuilt as tables, and blank lines were removed. Their wording and figures are unchanged.

| File | What it is |
|---|---|
| `01_Research_Source_Map_and_Reading_Plan.docx` | Which public sources answer which question, what to extract, alternative-data ideas, and the nowcast sourcing plan. |
| `02_Research_QA_Customers_Competitors_Suppliers.docx` | Researched answers on buyers, buyer qualification, competing options, suppliers, and constraints on building. |
| `03_AI_Chat_Log_Chart_Design_for_Industry_Map.docx` | Chat on how to present the industry map. This is where the trade-off charts came from. |
| `04_FRED_Data_Guide_and_Nowcast_Lag_Notes.docx` | The FRED series map, the structure-type distributed-lag method, and the Census lag benchmarks. |
| `05_AI_Chat_Log_PPI_Indexes_Simulator_and_KPI_Scope.pdf` | Chat export: the PPI construction index definitions, design of the supply/demand simulator, and how to scope "KPIs" in the brief. |
| `06_Prompt_Log_All_My_AI_Prompts.docx` | Every prompt I gave AI tools during the case study (the exported chats plus all 8 Claude Code sessions), with times and spelling corrected. This is the record behind the AI-use disclosure. |

## Old → new file names (reorganized 2026-11-20)

| Old location | New location |
|---|---|
| `MI_Data_Case_Study_Template.tex`, `sources.tex`, `Pnt72.pdf` | `01_Final_Deliverable/` (renamed as above) |
| `10k analysis.xlsx`, `Builder_100_2022_2026.xlsx` | `03_Analysis/Excel_Workbooks/` |
| `analysis/` | `03_Analysis/Case_Study_Charts/` |
| `housing_pipeline_nowcast/` | `03_Analysis/Housing_Starts_Nowcast_Model/` |
| `Macro analsis supply demand/` | `03_Analysis/Interactive_Supply_Demand_Simulator/` |
| `10ks/` (e.g. `DRHORTON_10k.pdf`) | `04_Source_Data/Company_10-K_Filings/` (e.g. `DR_Horton_10-K_FY2026.pdf`) |
| `CENSUS DATA ON PIPELINE/newresconst.pdf` | `04_Source_Data/Census_New_Residential_Construction/Census_New_Residential_Construction_Release_Oct-2026.pdf` |
| `Pipeline- time stage information/*_cust.xlsx` | `04_Source_Data/Census_Construction_Stage_Timing/Census_SOC_*.xlsx` |
| `FRED DATA/fredgraph.csv` | `04_Source_Data/FRED_Housing_Pipeline/FRED_Housing_Pipeline_…_1959-2026.csv` |
| `MACRO ECONOMIC DATA/`, `PRODUCER COSTS DATA/` | `04_Source_Data/Macro_Rates_Prices_Costs/` (the Census price-per-sq-ft article moved to `Census_New_Residential_Construction/`) |
| `Google Search Data/time_series_US_*.csv` | `04_Source_Data/Google_Trends/GoogleTrends_US_*.csv` |
| `RAW CHAT LOGS/`, `Reading Materials/`, `final deal.docx.pdf` | `05_Research_Notes_and_AI_Chat_Logs/` |

Two exact duplicates (a second copy of the Census release and a second copy of the simulator, both in `Reading Materials/`) and a leftover Excel lock file were moved to the macOS Trash. All script and LaTeX paths were updated to the new locations, and the scripts were re-run to confirm that they produce identical charts and data.
