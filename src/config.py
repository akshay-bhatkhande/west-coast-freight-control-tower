"""Frozen paths, zone lists, and default analysis parameters."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_LOOKUPS = ROOT / "data" / "lookups"

FAF_ZIP_NAME = "FAF5.7.1_2018-2024.zip"
FAF_ZIP_URL = (
    "https://faf.ornl.gov/faf5/Data/Download_Files/FAF5.7.1_2018-2024.zip"
)
FAF_STATE_ZIP_URL = (
    "https://faf.ornl.gov/faf5/Data/Download_Files/FAF5.7.1_State_2018-2024.zip"
)
FAF_EXTRACT_DIR = DATA_RAW / "faf5_2018_2024"
FAF_CSV_NAME = "FAF5.7.1_2018-2024.csv"
FAF_METADATA_NAME = "FAF5_metadata.xlsx"
FAF_VERSION = "FAF5.7.1"

PROCESSED_PARQUET = DATA_PROCESSED / "wc_faf_flows.parquet"
PROCESSED_DUCKDB = DATA_PROCESSED / "wc_faf.duckdb"

YEARS = list(range(2018, 2025))
DEFAULT_YEAR = 2024
DEFAULT_TRADE_TYPE = 1  # Domestic
DEFAULT_SCENARIO_PCT = 10
SCENARIO_MAX_PCT = 50

# FAF5 domestic zones — West Coast freeze (spec §2.3)
WEST_COAST_ZONES: dict[int, str] = {
    61: "Los Angeles CA",
    62: "Sacramento CA",
    63: "San Diego CA",
    64: "San Francisco CA",
    65: "Fresno CA",
    69: "Rest of CA",
    411: "Portland OR–WA (OR)",
    419: "Rest of OR",
    531: "Seattle WA",
    532: "Portland OR–WA (WA)",
    539: "Rest of WA",
}

WEST_COAST_ZONE_IDS = frozenset(WEST_COAST_ZONES.keys())

# Hero corridor: Bay Area ↔ Seattle–Tacoma
HERO_ORIG = 64
HERO_DEST = 531

MODE_LABELS: dict[int, str] = {
    1: "Truck",
    2: "Rail",
    3: "Water",
    4: "Air (incl. truck-air)",
    5: "Multiple modes & mail",
    6: "Pipeline",
    7: "Other and unknown",
    8: "No domestic mode",
}

TRADE_TYPE_LABELS: dict[int, str] = {
    1: "Domestic",
    2: "Import",
    3: "Export",
}

# Consistent palette across charts (Truck / Rail emphasis)
MODE_COLORS: dict[str, str] = {
    "Truck": "#C45C26",
    "Rail": "#1B4F72",
    "Water": "#2E86AB",
    "Air (incl. truck-air)": "#6C757D",
    "Multiple modes & mail": "#8B7355",
    "Pipeline": "#5D6D7E",
    "Other and unknown": "#95A5A6",
    "No domestic mode": "#BDC3C7",
}

SCTG2_LABELS: dict[int, str] = {
    1: "Animals and fish",
    2: "Cereal grains",
    3: "Other agricultural products",
    4: "Animal feed, eggs, honey",
    5: "Meat, poultry, fish",
    6: "Milled grain products",
    7: "Other foodstuffs",
    8: "Alcoholic beverages",
    9: "Tobacco products",
    10: "Building stone",
    11: "Natural sands",
    12: "Gravel and crushed stone",
    13: "Nonmetallic minerals n.e.c.",
    14: "Metallic ores and concentrates",
    15: "Coal",
    16: "Crude petroleum",
    17: "Gasoline and aviation turbine fuel",
    18: "Fuel oils",
    19: "Coal and petroleum products n.e.c.",
    20: "Basic chemicals",
    21: "Pharmaceutical products",
    22: "Fertilizers",
    23: "Chemical products and preparations n.e.c.",
    24: "Plastics and rubber",
    25: "Logs and other wood in the rough",
    26: "Wood products",
    27: "Pulp, newsprint, paper, paperboard",
    28: "Paper or paperboard articles",
    29: "Printed products",
    30: "Textiles, leather, and articles",
    31: "Nonmetallic mineral products",
    32: "Base metal in primary or semi forms",
    33: "Articles of base metal",
    34: "Machinery",
    35: "Electronic and electrical equipment",
    36: "Motorized and other vehicles",
    37: "Transportation equipment n.e.c.",
    38: "Precision instruments and apparatus",
    39: "Furniture, mattresses, lamps",
    40: "Miscellaneous manufactured products",
    41: "Waste and scrap",
    43: "Mixed freight",
    99: "Unknown / other",
}

REQUIRED_PROCESSED_COLUMNS = [
    "dms_orig",
    "dms_dest",
    "dms_mode",
    "sctg2",
    "trade_type",
    "dist_band",
    "year",
    "tons",
    "value_2017usd",
    "value_current",
    "tmiles",
    "orig_label",
    "dest_label",
    "mode_label",
    "commodity_label",
    "trade_label",
]
