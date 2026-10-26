"""Truck→rail scenario invariants."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.kpis import apply_truck_rail_shift, filter_flows, mode_mix  # noqa: E402


@pytest.fixture
def sample() -> pd.DataFrame:
    return pd.read_csv(ROOT / "tests" / "fixtures" / "sample_flows.csv")


def test_scenario_p0_unchanged(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    after = apply_truck_rail_shift(df, pct=0)
    assert pytest.approx(after["tons"].sum(), rel=1e-9) == df["tons"].sum()
    before_modes = mode_mix(df, metric="tons").set_index("dms_mode")["tons"]
    after_modes = mode_mix(after, metric="tons").set_index("dms_mode")["tons"]
    for mode in before_modes.index:
        assert pytest.approx(after_modes.get(mode, 0), rel=1e-9) == before_modes[mode]


def test_scenario_p10_truck_down_rail_up(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    before = mode_mix(df, metric="tons").set_index("dms_mode")["tons"]
    after_df = apply_truck_rail_shift(df, pct=10)
    after = mode_mix(after_df, metric="tons").set_index("dms_mode")["tons"]

    truck_before = float(before.get(1, 0))
    truck_after = float(after.get(1, 0))
    rail_before = float(before.get(2, 0))
    rail_after = float(after.get(2, 0))

    delta_truck = truck_before - truck_after
    delta_rail = rail_after - rail_before
    assert delta_truck > 0
    assert pytest.approx(delta_truck, rel=1e-6) == delta_rail
    assert pytest.approx(delta_truck, rel=1e-6) == truck_before * 0.10

    # Other modes stable
    for mode in set(before.index) | set(after.index):
        if mode in (1, 2):
            continue
        assert pytest.approx(float(after.get(mode, 0)), rel=1e-6) == float(
            before.get(mode, 0)
        )

    # Total tons conserved
    assert pytest.approx(after_df["tons"].sum(), rel=1e-6) == df["tons"].sum()


def test_scenario_pct_bounds(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    with pytest.raises(ValueError):
        apply_truck_rail_shift(df, pct=51)
    with pytest.raises(ValueError):
        apply_truck_rail_shift(df, pct=-1)
