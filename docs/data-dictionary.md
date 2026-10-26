# Data dictionary — West Coast Freight Control Tower

## 1. Source & version

| Item | Value |
| --- | --- |
| Product | Freight Analysis Framework **FAF5.7.1** regional ODCM |
| Years | 2018–2024 (2024 preliminary in release notes) |
| URL | https://faf.ornl.gov/faf5/Data/Download_Files/FAF5.7.1_2018-2024.zip |
| Hub | https://www.bts.gov/faf |
| DOI | https://doi.org/10.21949/1529116 |
| License | U.S. Government work (public domain) |
| Citation | BTS / FHWA Freight Analysis Framework 5 (FAF5.7.1) |
| Retrieval | See `data/raw/SOURCE.txt` after `python scripts/download_faf.py` |

## 2. Grain

One raw row ≈ foreign origin × domestic origin × domestic destination × foreign destination × foreign modes × **domestic mode** × **SCTG2** × **trade type** × **distance band**, with year columns for tons / value / ton-miles.

**West Coast filter:** `dms_orig` and `dms_dest` both in the in-scope FAF domestic zones (below).  
**Default analytic slice:** `trade_type = 1` (Domestic). Full WC table (all trade types) is persisted so the UI can switch without re-download.

**Processed grain:** long-form `OD × mode × commodity × trade × dist_band × year`.

## 3. Raw fields (regional CSV)

| Column | Meaning | Notes |
| --- | --- | --- |
| `fr_orig` / `fr_dest` | Foreign O/D | Often empty on domestic rows |
| `dms_orig` / `dms_dest` | Domestic FAF zone | Zero-padded in CSV (`064`); cast to int |
| `fr_inmode` / `fr_outmode` | Foreign modes | Empty on domestic-only |
| `dms_mode` | Domestic mode | 1–8 |
| `sctg2` | Commodity (2-digit SCTG) | 01–43 / 99 |
| `trade_type` | 1 Domestic, 2 Import, 3 Export | |
| `dist_band` | Distance band | Code table in metadata |
| `tons_YYYY` | Thousand tons | ≥ 0 |
| `value_YYYY` | Million **2017 constant** $ | |
| `current_value_YYYY` | Million current $ | |
| `tmiles_YYYY` | Million ton-miles | |

## 4. Code tables (MVP)

### West Coast zones (in scope)

| Code | Label |
| --- | --- |
| 61 | Los Angeles CA |
| 62 | Sacramento CA |
| 63 | San Diego CA |
| 64 | San Francisco CA |
| 65 | Fresno CA |
| 69 | Rest of CA |
| 411 | Portland OR–WA (OR) |
| 419 | Rest of OR |
| 531 | Seattle WA |
| 532 | Portland OR–WA (WA) |
| 539 | Rest of WA |

National FAF5 has ~132 domestic zones; only the 11 above enter this product.

### Modes (`dms_mode`)

1 Truck · 2 Rail · 3 Water · 4 Air (incl. truck-air) · 5 Multiple modes & mail · 6 Pipeline · 7 Other and unknown · 8 No domestic mode

Committed copies: `data/lookups/{zones,modes,commodities,trade_types}.csv`.

## 5. Processed table — `wc_faf_flows`

Path: `data/processed/wc_faf_flows.parquet` (also `wc_faf.duckdb` with views `corridor_year`, `mode_year`, `commodity_year`).

| Column | Type | Description |
| --- | --- | --- |
| `dms_orig`, `dms_dest` | int | FAF zone codes |
| `dms_mode`, `sctg2`, `trade_type`, `dist_band` | int | Dimensions |
| `year` | int | 2018–2024 |
| `tons` | float | Thousand tons |
| `value_2017usd` | float | Million 2017$ |
| `value_current` | float | Million current $ |
| `tmiles` | float | Million ton-miles |
| `orig_label`, `dest_label` | str | Zone labels |
| `mode_label`, `commodity_label`, `trade_label` | str | Lookups |

Logical key: all dimension columns including `dist_band` and `year`.

## 6. Derived KPIs

- **Corridor tons (year Y):** sum `tons` for OD pair; both-directions aggregates `min/max` zone order.
- **Mode share:** mode metric / total metric for selection.
- **Commodity share:** likewise.
- **YoY %:** `(Y − Y−1) / Y−1`; undefined when prior = 0.
- **Top corridor share:** top corridor tons / selected WC tons.

## 7. Scenario fields

| Input | `pct` ∈ [0, 50], default 10 |
| --- | --- |
| `truck_tons_new` | `truck_tons × (1 − p/100)` |
| `rail_tons_new` | `rail_tons + truck_tons × (p/100)` |
| Other modes | Unchanged |
| Assumption | Instantaneous tonnage shift only — **no** capacity, cost, transit time, or diverted OD |

## 8. Known limitations

From BTS FAF FAQs and user guide:

- Not facility-level; CFS-hybrid regional geography.
- Commodity detail is coarse (SCTG2).
- Local roads / local growth scenarios may diverge from FAF.
- Annual estimates; 2024 preliminary and may revise.
- “Weekly” in this app = **briefing cadence**, not weekly FAF microdata.

## 9. What “weekly” means here

A logistics BA / ops analytics lead runs a **weekly review pack** using the latest annual FAF cut — concentration risk, mode mix, commodity drivers, one scenario. FAF itself is annual.
