"""Transform FAF5.7.1 regional ODCM → West Coast analysis parquet / DuckDB."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.config import (
    DATA_LOOKUPS,
    FAF_CSV_NAME,
    FAF_EXTRACT_DIR,
    FAF_METADATA_NAME,
    MODE_LABELS,
    PROCESSED_DUCKDB,
    PROCESSED_PARQUET,
    SCTG2_LABELS,
    TRADE_TYPE_LABELS,
    WEST_COAST_ZONE_IDS,
    WEST_COAST_ZONES,
    YEARS,
)

logger = logging.getLogger(__name__)


def write_lookups(metadata_path: Path | None = None) -> dict[str, Path]:
    """Write committed lookup CSVs from metadata xlsx when present, else config."""
    DATA_LOOKUPS.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    zones = pd.DataFrame(
        [{"dms_zone": k, "zone_label": v} for k, v in WEST_COAST_ZONES.items()]
    )
    modes = pd.DataFrame(
        [{"dms_mode": k, "mode_label": v} for k, v in MODE_LABELS.items()]
    )
    commodities = pd.DataFrame(
        [{"sctg2": k, "commodity_label": v} for k, v in SCTG2_LABELS.items()]
    )
    trade_types = pd.DataFrame(
        [{"trade_type": k, "trade_label": v} for k, v in TRADE_TYPE_LABELS.items()]
    )

    # Enrich labels from official metadata when available (prefer ORNL names).
    if metadata_path and metadata_path.exists():
        try:
            xl = pd.ExcelFile(metadata_path)
            sheet_map = {s.lower(): s for s in xl.sheet_names}

            def _find(substr: str) -> str | None:
                for key, name in sheet_map.items():
                    if substr in key:
                        return name
                return None

            zone_sheet = _find("zone") or _find("faf")
            if zone_sheet:
                zdf = pd.read_excel(xl, sheet_name=zone_sheet)
                zdf.columns = [str(c).strip().lower() for c in zdf.columns]
                code_col = next(
                    (c for c in zdf.columns if "id" in c or "code" in c or c == "zone"),
                    zdf.columns[0],
                )
                label_col = next(
                    (c for c in zdf.columns if "name" in c or "label" in c or "desc" in c),
                    zdf.columns[1] if len(zdf.columns) > 1 else zdf.columns[0],
                )
                zdf = zdf[[code_col, label_col]].dropna()
                zdf[code_col] = pd.to_numeric(zdf[code_col], errors="coerce")
                zdf = zdf.dropna(subset=[code_col])
                zdf[code_col] = zdf[code_col].astype(int)
                zdf = zdf[zdf[code_col].isin(WEST_COAST_ZONE_IDS)]
                if not zdf.empty:
                    zones = zdf.rename(
                        columns={code_col: "dms_zone", label_col: "zone_label"}
                    )

            mode_sheet = _find("mode")
            if mode_sheet:
                mdf = pd.read_excel(xl, sheet_name=mode_sheet)
                mdf.columns = [str(c).strip().lower() for c in mdf.columns]
                code_col = next(
                    (c for c in mdf.columns if "code" in c or "id" in c or "mode" == c),
                    mdf.columns[0],
                )
                label_col = next(
                    (c for c in mdf.columns if "desc" in c or "name" in c or "label" in c),
                    mdf.columns[1] if len(mdf.columns) > 1 else mdf.columns[0],
                )
                mdf = mdf[[code_col, label_col]].dropna()
                mdf[code_col] = pd.to_numeric(mdf[code_col], errors="coerce")
                mdf = mdf.dropna(subset=[code_col])
                mdf[code_col] = mdf[code_col].astype(int)
                if not mdf.empty:
                    modes = mdf.rename(
                        columns={code_col: "dms_mode", label_col: "mode_label"}
                    )

            commodity_sheet = _find("commodity") or _find("sctg")
            if commodity_sheet:
                cdf = pd.read_excel(xl, sheet_name=commodity_sheet)
                cdf.columns = [str(c).strip().lower() for c in cdf.columns]
                code_col = next(
                    (c for c in cdf.columns if "code" in c or "sctg" in c or "id" in c),
                    cdf.columns[0],
                )
                label_col = next(
                    (c for c in cdf.columns if "desc" in c or "name" in c or "label" in c),
                    cdf.columns[1] if len(cdf.columns) > 1 else cdf.columns[0],
                )
                cdf = cdf[[code_col, label_col]].dropna()
                cdf[code_col] = pd.to_numeric(cdf[code_col], errors="coerce")
                cdf = cdf.dropna(subset=[code_col])
                cdf[code_col] = cdf[code_col].astype(int)
                if not cdf.empty:
                    commodities = cdf.rename(
                        columns={code_col: "sctg2", label_col: "commodity_label"}
                    )
        except Exception as exc:  # noqa: BLE001 — fallback to config labels
            logger.warning("Metadata parse failed (%s); using config labels", exc)

    paths["zones"] = DATA_LOOKUPS / "zones.csv"
    paths["modes"] = DATA_LOOKUPS / "modes.csv"
    paths["commodities"] = DATA_LOOKUPS / "commodities.csv"
    paths["trade_types"] = DATA_LOOKUPS / "trade_types.csv"

    zones.to_csv(paths["zones"], index=False)
    modes.to_csv(paths["modes"], index=False)
    commodities.to_csv(paths["commodities"], index=False)
    trade_types.to_csv(paths["trade_types"], index=False)
    return paths


def _zone_list_sql() -> str:
    return ", ".join(str(z) for z in sorted(WEST_COAST_ZONE_IDS))


def build_processed_tables(
    csv_path: Path | None = None,
    metadata_path: Path | None = None,
) -> Path:
    """Filter West Coast ODCM, unpivot years, join labels, write parquet + DuckDB."""
    csv_path = csv_path or (FAF_EXTRACT_DIR / FAF_CSV_NAME)
    metadata_path = metadata_path or (FAF_EXTRACT_DIR / FAF_METADATA_NAME)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing FAF CSV at {csv_path}. Run: python scripts/download_faf.py"
        )

    write_lookups(metadata_path)
    PROCESSED_PARQUET.parent.mkdir(parents=True, exist_ok=True)

    zones_csv = (DATA_LOOKUPS / "zones.csv").as_posix()
    modes_csv = (DATA_LOOKUPS / "modes.csv").as_posix()
    commodities_csv = (DATA_LOOKUPS / "commodities.csv").as_posix()
    trade_csv = (DATA_LOOKUPS / "trade_types.csv").as_posix()
    csv_posix = csv_path.as_posix()
    zone_list = _zone_list_sql()

    # Unpivot measure columns into long form inside DuckDB (filter pushdown).
    ton_cols = ", ".join(f"tons_{y}" for y in YEARS)
    val_cols = ", ".join(f"value_{y}" for y in YEARS)
    cur_cols = ", ".join(f"current_value_{y}" for y in YEARS)
    tm_cols = ", ".join(f"tmiles_{y}" for y in YEARS)

    con = duckdb.connect()
    pre_count = con.execute(
        f"SELECT COUNT(*) FROM read_csv_auto('{csv_posix}', header=true, sample_size=-1)"
    ).fetchone()[0]
    logger.info("FAF national ODCM rows: %s", pre_count)

    sql = f"""
    WITH raw AS (
      SELECT
        TRY_CAST(dms_orig AS INTEGER) AS dms_orig,
        TRY_CAST(dms_dest AS INTEGER) AS dms_dest,
        TRY_CAST(dms_mode AS INTEGER) AS dms_mode,
        TRY_CAST(sctg2 AS INTEGER) AS sctg2,
        TRY_CAST(trade_type AS INTEGER) AS trade_type,
        TRY_CAST(dist_band AS INTEGER) AS dist_band,
        {ton_cols},
        {val_cols},
        {cur_cols},
        {tm_cols}
      FROM read_csv_auto('{csv_posix}', header=true, sample_size=-1)
      WHERE TRY_CAST(dms_orig AS INTEGER) IN ({zone_list})
        AND TRY_CAST(dms_dest AS INTEGER) IN ({zone_list})
    ),
    keyed AS (
      SELECT *,
        list_value({", ".join(str(y) for y in YEARS)}) AS years,
        list_value({", ".join(f"tons_{y}" for y in YEARS)}) AS tons_list,
        list_value({", ".join(f"value_{y}" for y in YEARS)}) AS value_list,
        list_value({", ".join(f"current_value_{y}" for y in YEARS)}) AS current_list,
        list_value({", ".join(f"tmiles_{y}" for y in YEARS)}) AS tmiles_list
      FROM raw
    ),
    long AS (
      SELECT
        dms_orig, dms_dest, dms_mode, sctg2, trade_type, dist_band,
        UNNEST(years) AS year,
        UNNEST(tons_list) AS tons,
        UNNEST(value_list) AS value_2017usd,
        UNNEST(current_list) AS value_current,
        UNNEST(tmiles_list) AS tmiles
      FROM keyed
    )
    SELECT
      l.dms_orig,
      l.dms_dest,
      l.dms_mode,
      l.sctg2,
      l.trade_type,
      l.dist_band,
      CAST(l.year AS INTEGER) AS year,
      COALESCE(CAST(l.tons AS DOUBLE), 0) AS tons,
      COALESCE(CAST(l.value_2017usd AS DOUBLE), 0) AS value_2017usd,
      COALESCE(CAST(l.value_current AS DOUBLE), 0) AS value_current,
      COALESCE(CAST(l.tmiles AS DOUBLE), 0) AS tmiles,
      COALESCE(zo.zone_label, CAST(l.dms_orig AS VARCHAR)) AS orig_label,
      COALESCE(zd.zone_label, CAST(l.dms_dest AS VARCHAR)) AS dest_label,
      COALESCE(m.mode_label, CAST(l.dms_mode AS VARCHAR)) AS mode_label,
      COALESCE(c.commodity_label, CAST(l.sctg2 AS VARCHAR)) AS commodity_label,
      COALESCE(t.trade_label, CAST(l.trade_type AS VARCHAR)) AS trade_label
    FROM long l
    LEFT JOIN read_csv_auto('{zones_csv}', header=true) zo
      ON l.dms_orig = TRY_CAST(zo.dms_zone AS INTEGER)
    LEFT JOIN read_csv_auto('{zones_csv}', header=true) zd
      ON l.dms_dest = TRY_CAST(zd.dms_zone AS INTEGER)
    LEFT JOIN read_csv_auto('{modes_csv}', header=true) m
      ON l.dms_mode = TRY_CAST(m.dms_mode AS INTEGER)
    LEFT JOIN read_csv_auto('{commodities_csv}', header=true) c
      ON l.sctg2 = TRY_CAST(c.sctg2 AS INTEGER)
    LEFT JOIN read_csv_auto('{trade_csv}', header=true) t
      ON l.trade_type = TRY_CAST(t.trade_type AS INTEGER)
    """

    out_posix = PROCESSED_PARQUET.as_posix()
    con.execute(f"COPY ({sql}) TO '{out_posix}' (FORMAT PARQUET)")
    post_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_posix}')"
    ).fetchone()[0]
    year_check = con.execute(
        f"SELECT COUNT(DISTINCT year) FROM read_parquet('{out_posix}')"
    ).fetchone()[0]

    logger.info(
        "West Coast long-form rows: %s | distinct years: %s", post_count, year_check
    )
    if post_count == 0:
        raise RuntimeError("ETL produced 0 West Coast rows — check zone casting.")
    if year_check != len(YEARS):
        logger.warning("Expected %s years, found %s", len(YEARS), year_check)

    # Optional DuckDB warehouse with summary views
    if PROCESSED_DUCKDB.exists():
        PROCESSED_DUCKDB.unlink()
    db = duckdb.connect(PROCESSED_DUCKDB.as_posix())
    db.execute(
        f"CREATE TABLE wc_faf_flows AS SELECT * FROM read_parquet('{out_posix}')"
    )
    db.execute(
        """
        CREATE VIEW corridor_year AS
        SELECT year, trade_type, dms_orig, dms_dest, orig_label, dest_label,
               SUM(tons) AS tons, SUM(value_2017usd) AS value_2017usd,
               SUM(tmiles) AS tmiles
        FROM wc_faf_flows
        GROUP BY 1,2,3,4,5,6
        """
    )
    db.execute(
        """
        CREATE VIEW mode_year AS
        SELECT year, trade_type, dms_mode, mode_label,
               SUM(tons) AS tons, SUM(value_2017usd) AS value_2017usd
        FROM wc_faf_flows
        GROUP BY 1,2,3,4
        """
    )
    db.execute(
        """
        CREATE VIEW commodity_year AS
        SELECT year, trade_type, sctg2, commodity_label,
               SUM(tons) AS tons, SUM(value_2017usd) AS value_2017usd
        FROM wc_faf_flows
        GROUP BY 1,2,3,4
        """
    )
    db.close()
    con.close()

    # Persist ETL stats for build-log
    stats_path = PROCESSED_PARQUET.parent / "etl_stats.txt"
    stats_path.write_text(
        f"national_rows={pre_count}\n"
        f"wc_long_rows={post_count}\n"
        f"years={year_check}\n"
        f"parquet={PROCESSED_PARQUET}\n",
        encoding="utf-8",
    )
    return PROCESSED_PARQUET


def load_flows(path: Path | None = None) -> pd.DataFrame:
    """Load processed West Coast flows parquet."""
    path = path or PROCESSED_PARQUET
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: python scripts/download_faf.py && "
            "python scripts/build_tables.py"
        )
    return pd.read_parquet(path)
