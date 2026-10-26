"""KPI smoke tests on fixture data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.kpis import (  # noqa: E402
    commodity_mix,
    filter_flows,
    kpi_strip,
    mode_mix,
    top_corridors,
)


@pytest.fixture
def sample() -> pd.DataFrame:
    return pd.read_csv(ROOT / "tests" / "fixtures" / "sample_flows.csv")


def test_top_corridor_nonempty(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    top = top_corridors(df, metric="tons", n=5, both_directions=True)
    assert not top.empty
    assert "corridor" in top.columns
    assert top.iloc[0]["tons"] > 0


def test_kpi_strip_keys(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    k = kpi_strip(df, metric="tons")
    assert k["total_tons"] > 0
    assert 0 <= k["truck_share_tons"] <= 1
    assert k["top_corridor"] != "—"


def test_mode_mix_shares_sum(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    m = mode_mix(df, metric="tons")
    assert pytest.approx(m["share"].sum(), rel=1e-6) == 1.0


def test_commodity_mix(sample: pd.DataFrame):
    df = filter_flows(sample, year=2024, trade_type=1, exclude_intra=True)
    c = commodity_mix(df, metric="tons", n=3)
    assert len(c) >= 1


def test_import_smoke():
    import src.brief  # noqa: F401
    import src.config  # noqa: F401
    import src.etl  # noqa: F401
    import src.kpis  # noqa: F401
