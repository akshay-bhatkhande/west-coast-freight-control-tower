# Build log — West Coast Freight Control Tower

AI-assisted iteration with human-owned KPI calls. Short dated bullets.

## 2026-10-26 — Scaffold → ship

- **AI-proposed layout** matched frozen spec §4.2 (`app/Home.py`, `src/{config,etl,kpis,brief}`, `scripts/download_faf.py`, `scripts/build_tables.py`). Kept single-page Streamlit with clear section hierarchy instead of multi-page sprawl.
- **Download reliability:** Python `urllib` hit macOS SSL cert gaps; added curl fallback. Regional zip (~184 MB) retrieved successfully; state fallback unused.
- **ETL:** DuckDB `read_csv_auto` + West Coast zone pushdown on **2,494,901** national ODCM rows → **457,268** long-form WC rows (7 years). Metadata xlsx auto-parse failed on sheet shape; **kept config/lookup CSV labels** (human-validated against FAF5 mode/zone tables in the research freeze).
- **Human KPI validation:** Confirmed units (thousand tons / million 2017$) in every chart title; truck→rail scenario conserves total tons; `p=0` identity and `p=10` equal truck↓/rail↑ deltas covered by pytest.
- **Ops-manager critique pass (before → after):**
  - Before: risk of “dashboard of cards” and ton-miles as a hero metric.
  - After: 4-metric strip only; ton-miles demoted to methods expander; permanent scenario assumption callout; Weekly Ops Review as the stakeholder pack.
- **Findings locked for README** from 2024 domestic WC inter-zone slice: metro↔rest-of-state concentration; ~64% truck / ~3% rail; tons vs value commodity reorder; Bay↔SeaTac ~88% truck.
- **Tests:** 14 passed on fixtures; integration mark skips cleanly when parquet absent, runs when present.
- **Cut enforced:** no maps, no FAF6, no forecasts, no ML, no paid APIs.
