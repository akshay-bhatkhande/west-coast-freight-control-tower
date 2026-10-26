"""West Coast Freight Control Tower — Streamlit entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import (  # noqa: E402
    commodity_bar,
    corridor_bar,
    mode_donut,
    scenario_before_after,
)
from src.brief import generate_ops_brief  # noqa: E402
from src.config import (  # noqa: E402
    DEFAULT_SCENARIO_PCT,
    DEFAULT_YEAR,
    HERO_DEST,
    HERO_ORIG,
    PROCESSED_PARQUET,
    SCENARIO_MAX_PCT,
    TRADE_TYPE_LABELS,
    WEST_COAST_ZONES,
    YEARS,
)
from src.kpis import (  # noqa: E402
    apply_truck_rail_shift,
    commodity_mix,
    corridor_yoy,
    filter_flows,
    kpi_strip,
    mode_mix,
    scenario_delta_table,
)

st.set_page_config(
    page_title="West Coast Freight Control Tower",
    page_icon=":truck:",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@600;700&display=swap');

:root {
  --ink: #0F1C2E;
  --muted: #4A5B6E;
  --panel: #FFFFFF;
  --accent: #0E6B8A;
  --rail: #1B4F72;
  --truck: #D35400;
  --line: #C5D0DB;
  --wash: #E8EEF3;
}

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    linear-gradient(135deg, rgba(14,107,138,0.08) 0%, transparent 42%),
    linear-gradient(180deg, #F2F5F8 0%, #E4EBF1 55%, #DDE6EE 100%);
}

h1, h2, h3 {
  font-family: 'IBM Plex Serif', Georgia, serif !important;
  letter-spacing: -0.01em;
  color: var(--ink) !important;
}

.hero-brand {
  font-family: 'IBM Plex Serif', Georgia, serif;
  font-size: 2.35rem;
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 0.35rem 0;
  color: var(--ink);
}

.hero-sub {
  font-size: 1.02rem;
  color: var(--muted);
  max-width: 52rem;
  margin-bottom: 1.25rem;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin: 0.5rem 0 1.4rem 0;
}

.kpi {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 0.9rem 1rem;
  box-shadow: 0 1px 0 rgba(15,28,46,0.04);
}

.kpi .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.kpi .value {
  font-family: 'IBM Plex Serif', Georgia, serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--ink);
}

.kpi .hint {
  font-size: 0.8rem;
  color: var(--muted);
  margin-top: 0.25rem;
}

.callout {
  background: #EAF4F8;
  border-left: 4px solid var(--accent);
  padding: 0.85rem 1rem;
  margin: 0.75rem 0 1rem 0;
  color: var(--ink);
}

.section-rule {
  border: none;
  border-top: 1px solid var(--line);
  margin: 1.5rem 0 1rem 0;
}

@media (max-width: 900px) {
  .kpi-strip { grid-template-columns: 1fr 1fr; }
  .hero-brand { font-size: 1.75rem; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_PARQUET)


def render_missing_data() -> None:
    st.error("Processed West Coast flows not found.")
    st.markdown(
        """
Run these commands from the repo root, then refresh:

```bash
python scripts/download_faf.py
python scripts/build_tables.py
```
        """
    )
    st.stop()


def fmt_tons(x: float) -> str:
    return f"{x:,.0f}k t"


def fmt_value(x: float) -> str:
    return f"${x:,.0f}M"


# --- Header ---
st.markdown(
    '<p class="hero-brand">West Coast Freight Control Tower</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-sub">Ops analytics for Northern California / Bay Area ↔ '
    "Seattle–Tacoma and CA–OR–WA corridors — corridor concentration, mode mix, "
    "commodity drivers, and one defendable truck→rail scenario for the weekly review.</p>",
    unsafe_allow_html=True,
)

if not PROCESSED_PARQUET.exists():
    render_missing_data()

try:
    with st.spinner("Loading West Coast FAF flows…"):
        flows = load_data()
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load processed data: {exc}")
    st.stop()

if flows.empty:
    st.warning("Processed file is empty. Re-run `python scripts/build_tables.py`.")
    st.stop()

available_years = sorted(int(y) for y in flows["year"].dropna().unique())
default_year = DEFAULT_YEAR if DEFAULT_YEAR in available_years else available_years[-1]

# --- Sidebar filters ---
with st.sidebar:
    st.markdown("### Filters")
    year = st.selectbox("Year", available_years, index=available_years.index(default_year))
    trade_options = {
        TRADE_TYPE_LABELS.get(int(t), str(t)): int(t)
        for t in sorted(flows["trade_type"].dropna().unique())
    }
    # Prefer Domestic first
    trade_keys = list(trade_options.keys())
    if "Domestic" in trade_keys:
        trade_keys = ["Domestic"] + [k for k in trade_keys if k != "Domestic"]
    trade_label = st.selectbox("Trade type", trade_keys, index=0)
    trade_type = trade_options[trade_label]

    metric_choice = st.radio(
        "Metric focus",
        ["Tons", "Value (2017$)"],
        horizontal=True,
    )
    metric = "tons" if metric_choice == "Tons" else "value_2017usd"
    metric_label = (
        "Thousand tons" if metric == "tons" else "Million 2017$ value"
    )

    corridor_preset = st.selectbox(
        "Corridor preset",
        [
            "Hero: Bay Area ↔ Seattle–Tacoma",
            "All West Coast corridors (Top-10)",
            "Custom OD",
        ],
    )
    direction = st.radio("Direction", ["Both", "A → B", "B → A"], horizontal=True)
    both = direction == "Both"
    exclude_intra = st.checkbox("Exclude intra-zone flows", value=True)

    zone_ids = sorted(WEST_COAST_ZONES.keys())
    zone_labels = [f"{WEST_COAST_ZONES[z]} ({z})" for z in zone_ids]
    label_to_id = {f"{WEST_COAST_ZONES[z]} ({z})": z for z in zone_ids}

    custom_origins: list[int] | None = None
    custom_dests: list[int] | None = None
    geography_note = "West Coast internal OD matrix (CA / OR / WA FAF zones)"

    if corridor_preset.startswith("Hero"):
        if direction == "A → B":
            custom_origins, custom_dests = [HERO_ORIG], [HERO_DEST]
            both = False
        elif direction == "B → A":
            custom_origins, custom_dests = [HERO_DEST], [HERO_ORIG]
            both = False
        else:
            custom_origins, custom_dests = [HERO_ORIG], [HERO_DEST]
            both = True
        geography_note = "Hero corridor San Francisco CA ↔ Seattle WA (FAF 64↔531)"
    elif corridor_preset.startswith("Custom"):
        o_labs = st.multiselect(
            "Origins",
            zone_labels,
            default=[f"{WEST_COAST_ZONES[HERO_ORIG]} ({HERO_ORIG})"],
        )
        d_labs = st.multiselect(
            "Destinations",
            zone_labels,
            default=[f"{WEST_COAST_ZONES[HERO_DEST]} ({HERO_DEST})"],
        )
        custom_origins = [label_to_id[x] for x in o_labs]
        custom_dests = [label_to_id[x] for x in d_labs]
        both = direction == "Both"
        if direction == "B → A":
            custom_origins, custom_dests = custom_dests, custom_origins
            both = False
        elif direction == "A → B":
            both = False
        geography_note = "Custom West Coast OD selection"
    else:
        custom_origins = custom_dests = None
        geography_note = "All West Coast internal corridors (top-10 view)"

    scenario_pct = st.slider(
        "Truck → rail shift %",
        min_value=0,
        max_value=SCENARIO_MAX_PCT,
        value=DEFAULT_SCENARIO_PCT,
        help="Share of truck tons reassigned to rail on the current selection.",
    )

    if st.button("Reset to defaults"):
        st.cache_data.clear()
        st.rerun()

# Base year slice for WC (trade + intra filter); corridor applied after for "All"
try:
    if corridor_preset.startswith("All"):
        df_year = filter_flows(
            flows,
            year=year,
            trade_type=trade_type,
            exclude_intra=exclude_intra,
        )
        scenario_base = df_year
    else:
        if not custom_origins or not custom_dests:
            st.warning("No flows for this selection — pick at least one origin and destination.")
            if st.button("Reset filters"):
                st.rerun()
            st.stop()
        df_year = filter_flows(
            flows,
            year=year,
            trade_type=trade_type,
            origins=custom_origins,
            destinations=custom_dests,
            both_directions=both,
            exclude_intra=exclude_intra,
        )
        scenario_base = df_year
except Exception as exc:  # noqa: BLE001
    st.error(f"Filter error: {exc}")
    st.stop()

if df_year.empty:
    st.info("No flows for this selection.")
    if st.button("Clear selection / reset"):
        st.rerun()
    st.stop()

# KPI strip
kpis = kpi_strip(df_year, metric=metric, both_directions=True)
st.markdown(
    f"""
<div class="kpi-strip">
  <div class="kpi"><div class="label">Total tons ({year})</div>
    <div class="value">{fmt_tons(kpis['total_tons'])}</div>
    <div class="hint">FAF thousand-tons units</div></div>
  <div class="kpi"><div class="label">Total value ({year})</div>
    <div class="value">{fmt_value(kpis['total_value'])}</div>
    <div class="hint">Million 2017 constant $</div></div>
  <div class="kpi"><div class="label">Truck share of tons</div>
    <div class="value">{kpis['truck_share_tons']*100:.1f}%</div>
    <div class="hint">Mode dependence signal</div></div>
  <div class="kpi"><div class="label">Top corridor</div>
    <div class="value" style="font-size:1.05rem">{kpis['top_corridor']}</div>
    <div class="hint">{kpis['top_corridor_share']*100:.1f}% of selected tons</div></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

# Corridor concentration
st.subheader("Corridor concentration")
st.caption("Where tonnage and value sit across the West Coast internal matrix.")
try:
    # For corridor ranking use WC matrix at year (not just hero slice) when preset is All;
    # when hero/custom, show that selection's directional breakdown via top_corridors on df_year
    corridor_base = flows[flows["trade_type"] == trade_type]
    if exclude_intra:
        corridor_base = corridor_base[
            corridor_base["dms_orig"] != corridor_base["dms_dest"]
        ]
    corridors = corridor_yoy(
        corridor_base,
        year=year,
        metric=metric,
        n=10,
        both_directions=True,
    )
    if corridor_preset.startswith("Hero") or corridor_preset.startswith("Custom"):
        # Still show WC top-10 for context, highlight note
        st.caption("Chart shows Top-10 West Coast corridors for context; KPIs above reflect your selection.")
    fig = corridor_bar(corridors, metric, metric_label)
    st.plotly_chart(fig, use_container_width=True)
    show = corridors.copy()
    show["yoy_pct"] = show["yoy_pct"].apply(
        lambda x: "n/a" if x is None or x == float("inf") else f"{x*100:+.1f}%"
    )
    st.dataframe(
        show[
            ["corridor", "dms_orig", "dms_dest", metric, "share", "prior", "yoy_pct"]
        ].rename(
            columns={
                metric: metric_label,
                "share": "share_of_wc",
                "prior": f"{year-1}",
                "yoy_pct": "YoY",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
except Exception as exc:  # noqa: BLE001
    st.error(f"Corridor chart unavailable: {exc}")

st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

# Mode + commodity
c1, c2 = st.columns(2)
with c1:
    st.subheader("Mode mix")
    try:
        modes = mode_mix(df_year, metric=metric)
        st.plotly_chart(mode_donut(modes, metric, metric_label), use_container_width=True)
        st.dataframe(
            modes.assign(share=lambda d: (d["share"] * 100).round(1)).rename(
                columns={metric: metric_label, "share": "share_%"}
            ),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Mode chart unavailable: {exc}")

with c2:
    st.subheader("Commodity mix")
    commodity_metric = st.radio(
        "Commodity ranked by",
        ["Tons", "Value (2017$)"],
        horizontal=True,
        key="comm_metric",
    )
    cmetric = "tons" if commodity_metric == "Tons" else "value_2017usd"
    clabel = "Thousand tons" if cmetric == "tons" else "Million 2017$ value"
    try:
        commodities = commodity_mix(df_year, metric=cmetric, n=10)
        st.plotly_chart(
            commodity_bar(commodities, cmetric, clabel), use_container_width=True
        )
        tons_top = commodity_mix(df_year, metric="tons", n=1)
        val_top = commodity_mix(df_year, metric="value_2017usd", n=1)
        if (
            not tons_top.empty
            and not val_top.empty
            and tons_top.iloc[0]["commodity_label"] != val_top.iloc[0]["commodity_label"]
        ):
            st.caption(
                f"Note: tons leader is **{tons_top.iloc[0]['commodity_label']}**; "
                f"value leader is **{val_top.iloc[0]['commodity_label']}**."
            )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Commodity chart unavailable: {exc}")

st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

# Scenario
st.subheader("Mode-shift scenario")
st.markdown(
    f'<div class="callout"><strong>Assumption:</strong> instantaneous shift of '
    f"<strong>{scenario_pct}%</strong> of truck tons to rail on the current selection. "
    "No capacity, cost, transit time, or diverted OD effects. Tonnage only.</div>",
    unsafe_allow_html=True,
)
try:
    after = apply_truck_rail_shift(scenario_base, pct=float(scenario_pct))
    delta = scenario_delta_table(scenario_base, after, metric="tons")
    s1, s2 = st.columns([1.2, 1])
    with s1:
        st.plotly_chart(scenario_before_after(delta), use_container_width=True)
    with s2:
        truck_d = float(delta.loc[delta["dms_mode"] == 1, "delta"].sum()) if not delta.empty else 0.0
        rail_d = float(delta.loc[delta["dms_mode"] == 2, "delta"].sum()) if not delta.empty else 0.0
        st.metric("Truck tons Δ", f"{truck_d:,.1f} thousand tons")
        st.metric("Rail tons Δ", f"{rail_d:,.1f} thousand tons")
        st.dataframe(
            delta[
                ["mode_label", "before", "after", "delta", "share_before", "share_after"]
            ].assign(
                share_before=lambda d: (d["share_before"] * 100).round(1),
                share_after=lambda d: (d["share_after"] * 100).round(1),
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"At {scenario_pct}% shift, truck tonnage falls by {abs(truck_d):,.1f} thousand tons "
            f"and rail rises by the same amount on this selection."
        )
except Exception as exc:  # noqa: BLE001
    st.error(f"Scenario panel unavailable: {exc}")

st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

# Weekly ops brief
st.subheader("Weekly Ops Review")
st.caption("Auto-generated stakeholder pack from the active filters.")
try:
    brief_all = flows[flows["trade_type"] == trade_type]
    if exclude_intra:
        brief_all = brief_all[brief_all["dms_orig"] != brief_all["dms_dest"]]
    brief_md = generate_ops_brief(
        df_year,
        brief_all,
        year=year,
        trade_label=trade_label,
        metric=metric_choice,
        geography_note=geography_note,
        scenario_pct=float(scenario_pct),
        both_directions=True,
    )
    st.markdown(brief_md)
    st.download_button(
        "Download brief (.md)",
        data=brief_md,
        file_name=f"wc_freight_ops_brief_{year}.md",
        mime="text/markdown",
    )
except Exception as exc:  # noqa: BLE001
    st.error(f"Brief generation failed: {exc}")

st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

# Data & methods
with st.expander("Data & methods", expanded=False):
    st.markdown(
        f"""
**Source:** BTS/FHWA Freight Analysis Framework **FAF5.7.1** regional ODCM, years {YEARS[0]}–{YEARS[-1]}.  
**Download:** `https://faf.ornl.gov/faf5/Data/Download_Files/FAF5.7.1_2018-2024.zip`  
**Grain:** origin × destination × commodity (SCTG2) × mode × trade type × distance band × year.  
**Geography:** West Coast FAF domestic zones only (codes {", ".join(str(z) for z in sorted(WEST_COAST_ZONES))}).  
**Units:** `tons` = thousand tons; `value_2017usd` = million 2017 constant dollars; `tmiles` = million ton-miles.  
**Default slice:** domestic (`trade_type=1`).  

**Limitations:** FAF is a modeled regional estimate — not facility-level or true weekly shipment microdata.  
“Weekly” = briefing cadence. 2024 figures are preliminary in the 5.7.1 release.  
See `docs/data-dictionary.md` for full field definitions.
        """
    )
    with st.expander("Ton-miles (secondary)"):
        tm = mode_mix(df_year, metric="tmiles")
        st.dataframe(tm, use_container_width=True, hide_index=True)
