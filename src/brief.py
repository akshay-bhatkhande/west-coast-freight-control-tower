"""Weekly Ops Review markdown brief from active filters."""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.kpis import (
    commodity_mix,
    kpi_strip,
    largest_yoy_swings,
    mode_mix,
    scenario_delta_table,
    apply_truck_rail_shift,
)


def _fmt_tons(x: float) -> str:
    # FAF tons_* are thousand tons
    return f"{x:,.1f} thousand tons"


def _fmt_value(x: float) -> str:
    # million 2017$
    return f"${x:,.1f}M (2017$)"


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    if x == float("inf"):
        return "n/a (zero baseline)"
    return f"{x * 100:+.1f}%"


def generate_ops_brief(
    df_year: pd.DataFrame,
    df_all: pd.DataFrame,
    *,
    year: int,
    trade_label: str,
    metric: str,
    geography_note: str,
    scenario_pct: float,
    both_directions: bool = True,
) -> str:
    """Build stakeholder weekly ops review markdown."""
    kpis = kpi_strip(df_year, metric=metric, both_directions=both_directions)
    modes = mode_mix(df_year, metric="tons")
    commodities_tons = commodity_mix(df_year, metric="tons", n=5)
    commodities_val = commodity_mix(df_year, metric="value_2017usd", n=5)
    swings = largest_yoy_swings(
        df_all[df_all["trade_type"].isin(df_year["trade_type"].unique())]
        if not df_year.empty
        else df_all,
        year=year,
        metric="tons",
        n=3,
        both_directions=both_directions,
    )

    truck_share = kpis["truck_share_tons"]
    top_mode = modes.iloc[0]["mode_label"] if not modes.empty else "—"
    top_mode_share = float(modes.iloc[0]["share"]) if not modes.empty else 0.0

    top_comm_tons = (
        commodities_tons.iloc[0]["commodity_label"] if not commodities_tons.empty else "—"
    )
    top_comm_val = (
        commodities_val.iloc[0]["commodity_label"] if not commodities_val.empty else "—"
    )
    mismatch = (
        top_comm_tons != top_comm_val
        and top_comm_tons != "—"
        and top_comm_val != "—"
    )

    after = apply_truck_rail_shift(df_year, pct=scenario_pct)
    delta = scenario_delta_table(df_year, after, metric="tons")
    truck_delta = 0.0
    rail_delta = 0.0
    if not delta.empty:
        t = delta[delta["dms_mode"] == 1]
        r = delta[delta["dms_mode"] == 2]
        truck_delta = float(t["delta"].sum()) if not t.empty else 0.0
        rail_delta = float(r["delta"].sum()) if not r.empty else 0.0

    watch_lines = []
    for row in swings.itertuples():
        watch_lines.append(
            f"- **{row.corridor}**: {_fmt_tons(float(row.tons))} in {year}; "
            f"Δ {_fmt_tons(float(row.delta))} ({_fmt_pct(row.yoy_pct)} YoY)"
        )
    if not watch_lines:
        watch_lines = ["- No corridor YoY swings available for this selection."]

    mismatch_line = (
        f"Tons leader is **{top_comm_tons}**; value leader is **{top_comm_val}** "
        "(value often reorders vs tons)."
        if mismatch
        else f"Top commodity by tons and value: **{top_comm_tons}**."
    )

    today = date.today().isoformat()
    return f"""# Weekly Ops Review — West Coast Freight

**Brief date:** {today}  
**Period:** Calendar year {year} (FAF5.7.1 annual estimates; 2024 preliminary)  
**Trade scope:** {trade_label}  
**Geography:** {geography_note}  
**Metric focus:** {metric}

---

## Headline

Top corridor: **{kpis["top_corridor"]}** — {kpis["top_corridor_share"] * 100:.1f}% of selected West Coast tons.

- Total tons: **{_fmt_tons(kpis["total_tons"])}**
- Total value: **{_fmt_value(kpis["total_value"])}**

## Mode mix

Dominant mode: **{top_mode}** ({top_mode_share * 100:.1f}% of tons).  
Truck dependence: **{truck_share * 100:.1f}%** of selected tons move by truck.

## Commodity drivers

{mismatch_line}

## Mode-shift scenario ({scenario_pct:.0f}% truck → rail)

Instantaneous tonnage reassignment on the current selection only — **no** capacity, cost, transit-time, or diverted-OD effects.

- Truck tons Δ: **{_fmt_tons(truck_delta)}**
- Rail tons Δ: **{_fmt_tons(rail_delta)}**

## Watchlist — largest YoY tonnage swings

{chr(10).join(watch_lines)}

## Limitations

FAF is a modeled, regional estimate — not facility-level shipment microdata.  
“Weekly” here means briefing cadence for ops stakeholders, not weekly FAF data.  
Commodity detail is coarse (SCTG2); local authority counts may diverge.  
Cite: BTS/FHWA Freight Analysis Framework 5 (FAF5.7.1).
"""
