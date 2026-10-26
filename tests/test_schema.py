"""Schema / grain / lookup tests (fixture-based)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    MODE_LABELS,
    REQUIRED_PROCESSED_COLUMNS,
    WEST_COAST_ZONE_IDS,
    WEST_COAST_ZONES,
    YEARS,
)
from src.kpis import assert_wc_zones  # noqa: E402


@pytest.fixture
def sample() -> pd.DataFrame:
    return pd.read_csv(ROOT / "tests" / "fixtures" / "sample_flows.csv")


def test_lookups_modes_present():
    modes = pd.read_csv(ROOT / "data" / "lookups" / "modes.csv")
    assert set(modes["dms_mode"]) >= set(MODE_LABELS.keys())
    assert set(range(1, 9)).issubset(set(modes["dms_mode"]))


def test_lookups_wc_zones_labeled():
    zones = pd.read_csv(ROOT / "data" / "lookups" / "zones.csv")
    assert set(zones["dms_zone"]) == set(WEST_COAST_ZONES.keys())
    assert zones["zone_label"].notna().all()


def test_fixture_schema(sample: pd.DataFrame):
    for col in REQUIRED_PROCESSED_COLUMNS:
        assert col in sample.columns, f"missing {col}"
    assert set(sample["year"]).issubset(set(YEARS) | {2023, 2024})


def test_fixture_wc_filter(sample: pd.DataFrame):
    assert assert_wc_zones(sample)
    assert set(sample["dms_orig"]).issubset(WEST_COAST_ZONE_IDS)
    assert set(sample["dms_dest"]).issubset(WEST_COAST_ZONE_IDS)


def test_nonneg_measures(sample: pd.DataFrame):
    assert (sample["tons"] >= 0).all()
    assert (sample["value_2017usd"] >= 0).all()
    assert (sample["tmiles"] >= 0).all()


@pytest.mark.integration
def test_processed_parquet_if_present():
    path = ROOT / "data" / "processed" / "wc_faf_flows.parquet"
    if not path.exists():
        pytest.skip("processed parquet not built")
    df = pd.read_parquet(path)
    for col in REQUIRED_PROCESSED_COLUMNS:
        assert col in df.columns
    assert set(df["year"].unique()) >= set(YEARS)
    assert assert_wc_zones(df)
    assert (df["tons"] >= 0).all()
    assert len(df) > 0
