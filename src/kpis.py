"""Corridor / mode / commodity KPIs and truck→rail scenario."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.config import HERO_DEST, HERO_ORIG, MODE_LABELS, WEST_COAST_ZONE_IDS


MetricCol = str  # "tons" | "value_2017usd" | "tmiles"


def filter_flows(
    df: pd.DataFrame,
    *,
    year: int | None = None,
    trade_type: int | None = 1,
    origins: Iterable[int] | None = None,
    destinations: Iterable[int] | None = None,
    both_directions: bool = True,
    exclude_intra: bool = True,
) -> pd.DataFrame:
    """Apply control-tower filters. Corridor OD uses both_directions when True."""
    out = df.copy()
    if year is not None:
        out = out[out["year"] == year]
    if trade_type is not None:
        out = out[out["trade_type"] == trade_type]
    if exclude_intra:
        out = out[out["dms_orig"] != out["dms_dest"]]

    if origins is not None and destinations is not None:
        oset = set(origins)
        dset = set(destinations)
        if both_directions:
            mask = (
                (out["dms_orig"].isin(oset) & out["dms_dest"].isin(dset))
                | (out["dms_orig"].isin(dset) & out["dms_dest"].isin(oset))
            )
        else:
            mask = out["dms_orig"].isin(oset) & out["dms_dest"].isin(dset)
        out = out[mask]
    elif origins is not None:
        out = out[out["dms_orig"].isin(set(origins))]
    elif destinations is not None:
        out = out[out["dms_dest"].isin(set(destinations))]

    return out


def _metric_col(metric: str) -> MetricCol:
    """Normalize UI labels and aliases to a processed measure column."""
    if metric in ("tons", "value_2017usd", "value_current", "tmiles"):
        return metric
    key = metric.strip().lower().replace(" ", "")
    if key in ("tons", "ton", "thousandtons"):
        return "tons"
    if key in (
        "value",
        "value_2017",
        "value_2017usd",
        "value(2017$)",
        "value(2017usd)",
        "value2017$",
        "value2017",
    ):
        return "value_2017usd"
    if key in ("tmiles", "ton-miles", "tonmiles"):
        return "tmiles"
    if key in ("value_current", "currentvalue", "value(current$)"):
        return "value_current"
    return "tons"


def corridor_key(orig: int, dest: int, both: bool = True) -> tuple[int, int]:
    if both:
        return (min(orig, dest), max(orig, dest))
    return (orig, dest)


def top_corridors(
    df: pd.DataFrame,
    *,
    metric: str = "tons",
    n: int = 10,
    both_directions: bool = True,
) -> pd.DataFrame:
    """Rank OD corridors by metric; optionally collapse A↔B."""
    col = _metric_col(metric)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "dms_orig",
                "dms_dest",
                "orig_label",
                "dest_label",
                "corridor",
                col,
                "share",
            ]
        )

    work = df.copy()
    if both_directions:
        work["c_lo"] = work[["dms_orig", "dms_dest"]].min(axis=1)
        work["c_hi"] = work[["dms_orig", "dms_dest"]].max(axis=1)
        # Prefer labels from the lexicographically lower→higher direction present
        label_map = (
            work.assign(
                _ord=work["dms_orig"] * 10000 + work["dms_dest"]
            )
            .sort_values("_ord")
            .groupby(["c_lo", "c_hi"], as_index=False)
            .first()[["c_lo", "c_hi", "orig_label", "dest_label", "dms_orig", "dms_dest"]]
        )
        agg = (
            work.groupby(["c_lo", "c_hi"], as_index=False)[col]
            .sum()
            .merge(label_map, on=["c_lo", "c_hi"], how="left")
        )
        # Normalize labels to sorted zone order for display
        zone_labels = (
            pd.concat(
                [
                    work[["dms_orig", "orig_label"]].rename(
                        columns={"dms_orig": "z", "orig_label": "lab"}
                    ),
                    work[["dms_dest", "dest_label"]].rename(
                        columns={"dms_dest": "z", "dest_label": "lab"}
                    ),
                ]
            )
            .drop_duplicates("z")
            .set_index("z")["lab"]
            .to_dict()
        )
        agg["orig_label"] = agg["c_lo"].map(zone_labels)
        agg["dest_label"] = agg["c_hi"].map(zone_labels)
        agg["dms_orig"] = agg["c_lo"]
        agg["dms_dest"] = agg["c_hi"]
        agg["corridor"] = agg["orig_label"] + " ↔ " + agg["dest_label"]
        result = agg.sort_values(col, ascending=False).head(n)
    else:
        agg = (
            work.groupby(
                ["dms_orig", "dms_dest", "orig_label", "dest_label"], as_index=False
            )[col]
            .sum()
        )
        agg["corridor"] = agg["orig_label"] + " → " + agg["dest_label"]
        result = agg.sort_values(col, ascending=False).head(n)

    total = float(work[col].sum())
    result["share"] = result[col] / total if total else 0.0
    return result.reset_index(drop=True)


def mode_mix(df: pd.DataFrame, *, metric: str = "tons") -> pd.DataFrame:
    col = _metric_col(metric)
    if df.empty:
        return pd.DataFrame(columns=["dms_mode", "mode_label", col, "share"])
    agg = df.groupby(["dms_mode", "mode_label"], as_index=False)[col].sum()
    total = float(agg[col].sum())
    agg["share"] = agg[col] / total if total else 0.0
    return agg.sort_values(col, ascending=False).reset_index(drop=True)


def commodity_mix(
    df: pd.DataFrame, *, metric: str = "tons", n: int = 10
) -> pd.DataFrame:
    col = _metric_col(metric)
    if df.empty:
        return pd.DataFrame(columns=["sctg2", "commodity_label", col, "share"])
    agg = df.groupby(["sctg2", "commodity_label"], as_index=False)[col].sum()
    total = float(agg[col].sum())
    agg["share"] = agg[col] / total if total else 0.0
    return agg.sort_values(col, ascending=False).head(n).reset_index(drop=True)


def yoy_pct(current: float, prior: float) -> float | None:
    if prior == 0:
        return None if current == 0 else float("inf")
    return (current - prior) / prior


def corridor_yoy(
    df_all_years: pd.DataFrame,
    *,
    year: int,
    metric: str = "tons",
    n: int = 10,
    both_directions: bool = True,
) -> pd.DataFrame:
    """Top corridors for `year` with YoY % vs year-1."""
    col = _metric_col(metric)
    cur = top_corridors(
        df_all_years[df_all_years["year"] == year],
        metric=metric,
        n=50,
        both_directions=both_directions,
    )
    prior = top_corridors(
        df_all_years[df_all_years["year"] == year - 1],
        metric=metric,
        n=500,
        both_directions=both_directions,
    )
    if cur.empty:
        return cur
    prior_map = {
        (int(r.dms_orig), int(r.dms_dest)): float(getattr(r, col))
        for r in prior.itertuples()
    }
    cur = cur.head(n).copy()
    cur["prior"] = [
        prior_map.get((int(o), int(d)), 0.0)
        for o, d in zip(cur["dms_orig"], cur["dms_dest"])
    ]
    cur["yoy_pct"] = [
        yoy_pct(float(c), float(p)) for c, p in zip(cur[col], cur["prior"])
    ]
    return cur


def largest_yoy_swings(
    df_all_years: pd.DataFrame,
    *,
    year: int,
    metric: str = "tons",
    n: int = 3,
    both_directions: bool = True,
) -> pd.DataFrame:
    """Corridors with largest absolute YoY tonnage (or value) change."""
    col = _metric_col(metric)
    cur = top_corridors(
        df_all_years[df_all_years["year"] == year],
        metric=metric,
        n=200,
        both_directions=both_directions,
    )
    prior = top_corridors(
        df_all_years[df_all_years["year"] == year - 1],
        metric=metric,
        n=200,
        both_directions=both_directions,
    )
    if cur.empty:
        return cur
    prior_map = {
        (int(r.dms_orig), int(r.dms_dest)): float(getattr(r, col))
        for r in prior.itertuples()
    }
    cur = cur.copy()
    cur["prior"] = [
        prior_map.get((int(o), int(d)), 0.0)
        for o, d in zip(cur["dms_orig"], cur["dms_dest"])
    ]
    cur["delta"] = cur[col] - cur["prior"]
    cur["abs_delta"] = cur["delta"].abs()
    cur["yoy_pct"] = [
        yoy_pct(float(c), float(p)) for c, p in zip(cur[col], cur["prior"])
    ]
    return cur.sort_values("abs_delta", ascending=False).head(n).reset_index(drop=True)


def kpi_strip(
    df: pd.DataFrame,
    *,
    metric: str = "tons",
    both_directions: bool = True,
) -> dict:
    """Four headline KPIs for the control tower strip."""
    col = _metric_col(metric)
    total_tons = float(df["tons"].sum()) if not df.empty else 0.0
    total_value = float(df["value_2017usd"].sum()) if not df.empty else 0.0
    truck = df[df["dms_mode"] == 1]["tons"].sum() if not df.empty else 0.0
    truck_share = (float(truck) / total_tons) if total_tons else 0.0
    top = top_corridors(df, metric=metric, n=1, both_directions=both_directions)
    if top.empty:
        top_name, top_share = "—", 0.0
    else:
        top_name = str(top.iloc[0]["corridor"])
        top_share = float(top.iloc[0]["share"])
    return {
        "total_tons": total_tons,
        "total_value": total_value,
        "truck_share_tons": truck_share,
        "top_corridor": top_name,
        "top_corridor_share": top_share,
        "metric_total": float(df[col].sum()) if not df.empty else 0.0,
    }


def apply_truck_rail_shift(
    df: pd.DataFrame,
    *,
    pct: float,
) -> pd.DataFrame:
    """
    Shift `pct`% of truck tons to rail within the provided frame.

    Assumption: instantaneous tonnage reassignment only — no capacity, cost,
    transit time, or diverted OD effects.
    """
    if df.empty or pct == 0:
        return df.copy()
    if pct < 0 or pct > 50:
        raise ValueError("Scenario pct must be in [0, 50]")

    work = df.copy()
    # Aggregate to mode for the selection, then redistribute tons
    mode_tons = work.groupby("dms_mode", as_index=False)["tons"].sum()
    truck_row = mode_tons[mode_tons["dms_mode"] == 1]
    rail_row = mode_tons[mode_tons["dms_mode"] == 2]
    truck_tons = float(truck_row["tons"].sum()) if not truck_row.empty else 0.0
    shift = truck_tons * (pct / 100.0)

    # Scale truck rows down and add synthetic rail adjustment rows proportional
    # to existing rail commodity mix when possible; else add a residual row.
    if truck_tons > 0 and shift > 0:
        truck_mask = work["dms_mode"] == 1
        scale = 1.0 - (pct / 100.0)
        work.loc[truck_mask, "tons"] = work.loc[truck_mask, "tons"] * scale

        rail_mask = work["dms_mode"] == 2
        if rail_mask.any() and float(work.loc[rail_mask, "tons"].sum()) > 0:
            rail_total = float(work.loc[rail_mask, "tons"].sum())
            weights = work.loc[rail_mask, "tons"] / rail_total
            work.loc[rail_mask, "tons"] = work.loc[rail_mask, "tons"] + weights * shift
        else:
            # Create a single residual rail row from a truck template
            template = work[truck_mask].iloc[0].copy()
            template["dms_mode"] = 2
            template["mode_label"] = MODE_LABELS[2]
            template["tons"] = shift
            template["value_2017usd"] = 0.0
            template["value_current"] = 0.0
            template["tmiles"] = 0.0
            work = pd.concat([work, pd.DataFrame([template])], ignore_index=True)

    return work


def scenario_delta_table(
    before: pd.DataFrame,
    after: pd.DataFrame,
    *,
    metric: str = "tons",
) -> pd.DataFrame:
    """Before/after mode shares for the scenario panel."""
    col = _metric_col(metric)
    b = mode_mix(before, metric=metric).rename(
        columns={col: "before", "share": "share_before"}
    )
    a = mode_mix(after, metric=metric).rename(
        columns={col: "after", "share": "share_after"}
    )
    out = b.merge(a, on=["dms_mode", "mode_label"], how="outer").fillna(0.0)
    out["delta"] = out["after"] - out["before"]
    out["delta_share"] = out["share_after"] - out["share_before"]
    return out.sort_values("dms_mode").reset_index(drop=True)


def assert_wc_zones(df: pd.DataFrame) -> bool:
    """True if all OD zones are in the West Coast freeze set."""
    return (
        set(df["dms_orig"].unique()).issubset(WEST_COAST_ZONE_IDS)
        and set(df["dms_dest"].unique()).issubset(WEST_COAST_ZONE_IDS)
    )


def hero_corridor_slice(
    df: pd.DataFrame,
    *,
    year: int,
    trade_type: int = 1,
    both_directions: bool = True,
) -> pd.DataFrame:
    return filter_flows(
        df,
        year=year,
        trade_type=trade_type,
        origins=[HERO_ORIG],
        destinations=[HERO_DEST],
        both_directions=both_directions,
        exclude_intra=True,
    )
