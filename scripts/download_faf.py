#!/usr/bin/env python3
"""Download and extract FAF5.7.1 regional 2018–2024 ODCM (idempotent)."""

from __future__ import annotations

import argparse
import ssl
import sys
import zipfile
from datetime import date
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

try:
    import certifi  # type: ignore

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    # macOS python.org installs often lack system certs; fall back carefully.
    _SSL_CONTEXT = ssl.create_default_context()
    try:
        _SSL_CONTEXT.load_default_certs()
    except Exception:  # noqa: BLE001
        _SSL_CONTEXT = ssl._create_unverified_context()  # noqa: S323

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    DATA_RAW,
    FAF_CSV_NAME,
    FAF_EXTRACT_DIR,
    FAF_METADATA_NAME,
    FAF_STATE_ZIP_URL,
    FAF_VERSION,
    FAF_ZIP_NAME,
    FAF_ZIP_URL,
)


def _download_curl(url: str, dest: Path) -> None:
    """Prefer system curl when Python SSL certs are missing (common on macOS)."""
    import shutil
    import subprocess

    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl not found")
    print(f"Downloading via curl {url}")
    print(f"  → {dest}")
    subprocess.run(
        [curl, "-L", "--fail", "--retry", "3", "--retry-delay", "4", "-o", str(dest), url],
        check=True,
    )
    print(f"Saved {dest.stat().st_size / 1e6:.1f} MB")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    print(f"Downloading {url}")
    print(f"  → {dest}")
    try:
        req = Request(url, headers={"User-Agent": "west-coast-freight-control-tower/0.1"})
        with urlopen(req, timeout=600, context=_SSL_CONTEXT) as resp, open(tmp, "wb") as fh:
            total = resp.headers.get("Content-Length")
            total_n = int(total) if total and total.isdigit() else None
            written = 0
            block = 1024 * 1024
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                if total_n:
                    pct = 100.0 * written / total_n
                    print(
                        f"\r  {written / 1e6:.1f} / {total_n / 1e6:.1f} MB ({pct:.0f}%)",
                        end="",
                    )
                else:
                    print(f"\r  {written / 1e6:.1f} MB", end="")
        print()
        tmp.replace(dest)
        print(f"Saved {dest.stat().st_size / 1e6:.1f} MB")
    except Exception as exc:  # noqa: BLE001
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        print(f"urllib download failed ({exc}); trying curl…")
        _download_curl(url, dest)


def _extract(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    print(f"Extracted to {extract_dir}")


def _write_source(url: str, used_fallback: bool) -> None:
    source = DATA_RAW / "SOURCE.txt"
    note = (
        "FALLBACK: state-level zip used — Bay Area collapsed into California.\n"
        if used_fallback
        else ""
    )
    source.write_text(
        f"product={FAF_VERSION} Regional ODCM 2018-2024\n"
        f"url={url}\n"
        f"retrieved={date.today().isoformat()}\n"
        f"citation=U.S. Bureau of Transportation Statistics / FHWA Freight Analysis Framework 5 "
        f"(FAF5.7.1). Public domain U.S. Government work.\n"
        f"hub=https://www.bts.gov/faf\n"
        f"doi=https://doi.org/10.21949/1529116\n"
        f"{note}",
        encoding="utf-8",
    )
    print(f"Wrote {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and re-extract even if files exist",
    )
    parser.add_argument(
        "--fallback-state",
        action="store_true",
        help="Use state-level zip (loses Bay Area vs Rest-of-CA split)",
    )
    args = parser.parse_args()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_RAW / FAF_ZIP_NAME
    csv_path = FAF_EXTRACT_DIR / FAF_CSV_NAME
    meta_path = FAF_EXTRACT_DIR / FAF_METADATA_NAME
    url = FAF_STATE_ZIP_URL if args.fallback_state else FAF_ZIP_URL
    used_fallback = bool(args.fallback_state)

    if args.fallback_state:
        zip_path = DATA_RAW / "FAF5.7.1_State_2018-2024.zip"

    need_download = args.force or not zip_path.exists()
    need_extract = args.force or not csv_path.exists() or not meta_path.exists()

    if not need_download and not need_extract:
        print("FAF zip + extracted CSV already present; skipping (use --force to refresh).")
        if not (DATA_RAW / "SOURCE.txt").exists():
            _write_source(url, used_fallback)
        return 0

    if need_download:
        try:
            _download(url, zip_path)
        except (URLError, HTTPError, TimeoutError) as exc:
            if used_fallback:
                print(f"ERROR: download failed: {exc}", file=sys.stderr)
                return 1
            print(f"Regional download failed ({exc}); trying state fallback…")
            url = FAF_STATE_ZIP_URL
            zip_path = DATA_RAW / "FAF5.7.1_State_2018-2024.zip"
            used_fallback = True
            try:
                _download(url, zip_path)
            except (URLError, HTTPError, TimeoutError) as exc2:
                print(f"ERROR: fallback download failed: {exc2}", file=sys.stderr)
                return 1

    if need_extract or need_download:
        _extract(zip_path, FAF_EXTRACT_DIR)
        # Some zips nest files; flatten if needed
        if not csv_path.exists():
            matches = list(FAF_EXTRACT_DIR.rglob("FAF5.7.1_*2018-2024.csv"))
            if matches:
                target = FAF_EXTRACT_DIR / FAF_CSV_NAME
                if matches[0] != target:
                    matches[0].replace(target)
            meta_matches = list(FAF_EXTRACT_DIR.rglob("FAF5_metadata.xlsx"))
            if meta_matches and not meta_path.exists():
                meta_matches[0].replace(meta_path)

    if not (FAF_EXTRACT_DIR / FAF_CSV_NAME).exists() and not list(
        FAF_EXTRACT_DIR.rglob("*.csv")
    ):
        print("ERROR: no CSV found after extract", file=sys.stderr)
        return 1

    _write_source(url, used_fallback)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
