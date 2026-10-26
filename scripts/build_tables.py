#!/usr/bin/env python3
"""Build West Coast analysis parquet + DuckDB from downloaded FAF CSV."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.etl import build_processed_tables  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    path = build_processed_tables()
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
