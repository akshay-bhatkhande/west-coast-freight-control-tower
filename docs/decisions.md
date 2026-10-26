# Decisions — West Coast Freight Control Tower

## Why FAF5.7.1 2018–2024 regional (not FAF6.0-only, not state-only)

- **Multi-year KPIs:** FAF5.7.1 ships annual 2018–2024 estimates, which supports YoY corridor swings and a credible “weekly ops” narrative. FAF6.0 (2022 benchmark) was a single base year at research freeze — useful later, not for this MVP.
- **Regional grain:** Bay Area (64) vs Rest of CA (69) and Seattle–Tacoma (531) are first-class FAF zones. State-only CSV collapses Bay Area into California and weakens the hero corridor story. State zip remains a documented download fallback only.
- **Forecast zips cut:** 2030–2050 / Hi-Lo are out of scope for an ops tower.

## Why domestic `trade_type=1` default

- Stakeholder persona is a logistics / SC ops BA reviewing **domestic corridor exposure** for weekly prioritization — not a foreign-trade entry/exit deep dive.
- Import/export remain in the processed table and UI trade filter so interviewers can explore without re-ETL.

## Why truck→rail tonnage shift (and what it is not)

- One defendable scenario is enough for planning conversations: “if X% of truck tons on this corridor moved to rail, how do mode shares change?”
- It is **not** a capacity model, cost model, emissions model, transit-time model, or OD diversion model. The UI surfaces that assumption permanently.

## Why no map

- Paid map tiles are forbidden; free Folium/OSM still burns polish time and invites facility-level over-interpretation of regional FAF zones.
- Horizontal bars with readable OD labels answer concentration without geospatial chrome.

## Rejected KPI ideas

| Idea | Why rejected |
| --- | --- |
| Ton-miles as hero metric | Harder to narrate in ops reviews; kept secondary in expander |
| National OD explorer | Dilutes West Coast story |
| Cost / CO₂ overlays | No free reliable OD cost layer in scope |
| ML anomaly detection | Wrong portfolio slot (F1 / NFL own ML) |
| County disaggregation | Size + quality caveats; grain mismatch |

## Stack choices

- **DuckDB** for filter-pushdown ETL on ~2.5M national rows without holding the full frame in pandas.
- **Parquet** as the Streamlit runtime source; optional DuckDB views for ad-hoc SQL.
- **Lookups committed as CSV** so runtime can stay lean even if metadata xlsx parse fails.
- **stdlib urllib + curl fallback** for download reliability on macOS Python SSL installs.
