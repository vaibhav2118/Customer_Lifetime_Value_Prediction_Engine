"""
pipelines/ingest.py
-------------------
Phase 1: Data ingestion pipeline for the Online Retail II dataset.

Steps:
  1. Download the XLSX file from UCI ML Repository (or skip if already present).
  2. Parse and clean the raw data.
  3. Persist cleaned transactions to data/processed/transactions.parquet.

Usage:
    python pipelines/ingest.py [--skip-download]
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_EXCEL = RAW_DIR / "online_retail_II.xlsx"
PROCESSED_PARQUET = PROCESSED_DIR / "transactions.parquet"

# UCI download URL (direct link to the zip that contains the xlsx)
DATA_URL = (
    "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_dataset(force: bool = False) -> Path:
    """Download the Online Retail II zip and extract the XLSX."""
    import zipfile
    import io

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_EXCEL.exists() and not force:
        log.info("Raw file already present: %s — skipping download.", RAW_EXCEL)
        return RAW_EXCEL

    log.info("Downloading dataset from UCI ML Repository…")
    response = requests.get(DATA_URL, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    buf = io.BytesIO()
    with tqdm(total=total, unit="B", unit_scale=True, desc="Downloading") as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            buf.write(chunk)
            pbar.update(len(chunk))

    log.info("Extracting ZIP archive…")
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        xlsx_names = [n for n in zf.namelist() if n.endswith(".xlsx")]
        if not xlsx_names:
            raise RuntimeError("No XLSX found inside the downloaded ZIP.")
        # Extract the first xlsx found
        target_name = xlsx_names[0]
        log.info("Extracting '%s'…", target_name)
        zf.extract(target_name, RAW_DIR)
        extracted_path = RAW_DIR / target_name
        if extracted_path != RAW_EXCEL:
            extracted_path.rename(RAW_EXCEL)

    log.info("Dataset saved to: %s", RAW_EXCEL)
    return RAW_EXCEL


# ---------------------------------------------------------------------------
# Load & Clean
# ---------------------------------------------------------------------------

def load_raw(path: Path) -> pd.DataFrame:
    """Load both sheets of the Online Retail II workbook."""
    log.info("Reading Excel file (this may take 30–60s for large files)…")
    sheets = []
    for sheet in ["Year 2009-2010", "Year 2010-2011"]:
        try:
            df = pd.read_excel(path, sheet_name=sheet, dtype={"Customer ID": str, "StockCode": str})
            df["source_sheet"] = sheet
            sheets.append(df)
            log.info("  Loaded sheet '%s': %d rows", sheet, len(df))
        except Exception as exc:
            log.warning("  Could not load sheet '%s': %s", sheet, exc)

    if not sheets:
        raise RuntimeError("Could not load any sheet from the workbook.")

    combined = pd.concat(sheets, ignore_index=True)
    log.info("Total raw rows: %d", len(combined))
    return combined


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning rules and return a clean DataFrame."""

    original_len = len(df)

    # ------------------------------------------------------------------ #
    # 1. Standardise column names
    # ------------------------------------------------------------------ #
    rename_map = {
        "Invoice": "InvoiceNo",
        "StockCode": "StockCode",
        "Description": "Description",
        "Quantity": "Quantity",
        "InvoiceDate": "InvoiceDate",
        "Price": "UnitPrice",
        "Customer ID": "CustomerID",
        "Country": "Country",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ------------------------------------------------------------------ #
    # 2. Drop mandatory-null rows
    # ------------------------------------------------------------------ #
    before = len(df)
    df = df.dropna(subset=["CustomerID", "Description"])
    log.info("Dropped %d rows with null CustomerID or Description.", before - len(df))

    # ------------------------------------------------------------------ #
    # 3. Remove cancellations (InvoiceNo starts with 'C')
    # ------------------------------------------------------------------ #
    before = len(df)
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    log.info("Dropped %d cancellation rows.", before - len(df))

    # ------------------------------------------------------------------ #
    # 4. Remove invalid quantities and prices
    # ------------------------------------------------------------------ #
    before = len(df)
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    log.info("Dropped %d rows with non-positive Quantity or Price.", before - len(df))

    # ------------------------------------------------------------------ #
    # 5. Parse dates
    # ------------------------------------------------------------------ #
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    n_bad_dates = df["InvoiceDate"].isna().sum()
    if n_bad_dates:
        log.warning("Dropping %d rows with unparseable dates.", n_bad_dates)
        df = df.dropna(subset=["InvoiceDate"])

    # ------------------------------------------------------------------ #
    # 6. Derived columns
    # ------------------------------------------------------------------ #
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["CustomerID"] = df["CustomerID"].astype(str).str.strip()
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    # StockCode has mixed int/str values (e.g. 79323 and 79323P) —
    # explicitly cast to str to prevent PyArrow int64 inference failure
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    if "source_sheet" in df.columns:
        df["source_sheet"] = df["source_sheet"].astype(str)

    # ------------------------------------------------------------------ #
    # 7. Remove statistical outliers in Revenue (> 99.9th percentile)
    # ------------------------------------------------------------------ #
    threshold = df["Revenue"].quantile(0.999)
    before = len(df)
    df = df[df["Revenue"] <= threshold]
    log.info(
        "Dropped %d extreme outlier rows (Revenue > %.2f).", before - len(df), threshold
    )

    log.info(
        "Cleaning complete: %d → %d rows (%.1f%% retained).",
        original_len,
        len(df),
        100 * len(df) / original_len,
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_processed(df: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_PARQUET, index=False)
    log.info("Saved cleaned transactions: %s (%d rows)", PROCESSED_PARQUET, len(df))
    return PROCESSED_PARQUET


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def print_summary(df: pd.DataFrame) -> None:
    log.info("=" * 60)
    log.info("DATASET SUMMARY")
    log.info("  Date range      : %s → %s", df["InvoiceDate"].min().date(), df["InvoiceDate"].max().date())
    log.info("  Unique customers: %d", df["CustomerID"].nunique())
    log.info("  Unique invoices : %d", df["InvoiceNo"].nunique())
    log.info("  Total revenue   : £{:,.2f}".format(df["Revenue"].sum()))
    log.info("  Countries       : %d", df["Country"].nunique())
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(skip_download: bool = False) -> pd.DataFrame:
    if not skip_download:
        download_dataset()
    elif not RAW_EXCEL.exists():
        log.error(
            "--skip-download set but raw file not found: %s\n"
            "Run without --skip-download first.",
            RAW_EXCEL,
        )
        sys.exit(1)

    df_raw = load_raw(RAW_EXCEL)
    df_clean = clean(df_raw)
    print_summary(df_clean)
    save_processed(df_clean)
    return df_clean


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest and clean Online Retail II data.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading if raw file already exists.",
    )
    args = parser.parse_args()
    main(skip_download=args.skip_download)
