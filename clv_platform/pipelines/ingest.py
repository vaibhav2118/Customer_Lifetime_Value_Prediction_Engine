import os
import argparse
import logging
from pathlib import Path
import pandas as pd
import requests
import zipfile
import io
from clv_platform.database.connection import SessionLocal, init_db
from clv_platform.services.ingestion import ingest_dataframe_to_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_EXCEL = RAW_DIR / "online_retail_II.xlsx"

# Standard Fallback path if already downloaded in retail_clv
FALLBACK_EXCEL = PROJECT_ROOT.parent / "retail_clv" / "data" / "raw" / "online_retail_II.xlsx"

DATA_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"

def download_dataset(force: bool = False) -> Path:
    """Download the Online Retail II zip and extract the XLSX."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_EXCEL.exists() and not force:
        log.info("Raw file already present in platform: %s", RAW_EXCEL)
        return RAW_EXCEL

    if FALLBACK_EXCEL.exists() and not force:
        log.info("Found existing raw file in retail_clv: %s. Copying it...", FALLBACK_EXCEL)
        import shutil
        shutil.copy2(FALLBACK_EXCEL, RAW_EXCEL)
        return RAW_EXCEL

    log.info("Downloading dataset from UCI ML Repository...")
    response = requests.get(DATA_URL, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    buf = io.BytesIO()
    for chunk in response.iter_content(chunk_size=8192):
        buf.write(chunk)

    log.info("Extracting ZIP archive...")
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        xlsx_names = [n for n in zf.namelist() if n.endswith(".xlsx")]
        if not xlsx_names:
            raise RuntimeError("No XLSX found inside the downloaded ZIP.")
        target_name = xlsx_names[0]
        zf.extract(target_name, RAW_DIR)
        extracted_path = RAW_DIR / target_name
        if extracted_path != RAW_EXCEL:
            extracted_path.rename(RAW_EXCEL)

    log.info("Dataset saved to: %s", RAW_EXCEL)
    return RAW_EXCEL

def run_ingestion(limit_rows: int = None):
    # Initialize DB schemas
    init_db()
    
    # 1. Download
    excel_path = download_dataset()
    
    # 2. Load
    log.info("Loading Sheets from Excel: %s", excel_path)
    # Sheet 0 is Year 2009-2010, Sheet 1 is Year 2010-2011
    # For speed and testing, allow limit_rows
    df_list = []
    
    # Read both sheets
    for sheet_name in ["Year 2009-2010", "Year 2010-2011"]:
        try:
            log.info("Parsing sheet: %s", sheet_name)
            df_sheet = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=limit_rows, dtype={"Customer ID": str, "StockCode": str})
            df_list.append(df_sheet)
        except Exception as e:
            log.warning("Could not read sheet %s: %s. Trying sheet index fallback...", sheet_name, e)
            
    if not df_list:
        # Fallback to sheet index
        for idx in [0, 1]:
            df_sheet = pd.read_excel(excel_path, sheet_name=idx, nrows=limit_rows)
            df_list.append(df_sheet)
            
    df_all = pd.concat(df_list, ignore_index=True)
    log.info("Successfully loaded %d raw rows.", len(df_all))
    
    # Ingest to DB
    db = SessionLocal()
    try:
        results = ingest_dataframe_to_db(df_all, db)
        log.info("Database ingestion results: %s", results)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-rows", type=int, default=None, help="Limit rows to read for testing")
    args = parser.parse_args()
    run_ingestion(limit_rows=args.limit_rows)
