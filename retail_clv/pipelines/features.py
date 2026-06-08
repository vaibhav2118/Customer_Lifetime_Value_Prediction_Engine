"""
pipelines/features.py
---------------------
Phase 2: RFM + extended feature engineering.

Reads cleaned transactions from data/processed/transactions.parquet and
produces an RFM feature table saved to data/processed/rfm_features.parquet.

Features computed per customer:
  - recency        : days since last purchase (relative to snapshot date)
  - frequency      : number of repeat transactions (n_invoices - 1, BG/NBD convention)
  - T              : customer age in days (first purchase → snapshot)
  - monetary_value : mean revenue per transaction (BG/NBD input)
  - total_revenue  : cumulative spend
  - n_invoices     : raw invoice count
  - aov            : average order value (= monetary_value)
  - purchase_std   : std deviation of per-invoice revenue (volatility proxy)
  - days_active    : span between first and last purchase
  - avg_days_between_purchases
  - country        : mode country for the customer

Usage:
    python pipelines/features.py
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TRANSACTIONS_PATH = PROCESSED_DIR / "transactions.parquet"
RFM_PATH = PROCESSED_DIR / "rfm_features.parquet"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-invoice aggregation helper
# ---------------------------------------------------------------------------

def _invoice_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per (CustomerID, InvoiceNo) with InvoiceDate + Revenue."""
    return (
        df.groupby(["CustomerID", "InvoiceNo"])
        .agg(
            invoice_date=("InvoiceDate", "min"),
            invoice_revenue=("Revenue", "sum"),
        )
        .reset_index()
    )


# ---------------------------------------------------------------------------
# RFM computation
# ---------------------------------------------------------------------------

def compute_rfm(df: pd.DataFrame, snapshot_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Compute RFM and extended features.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transactions with columns [CustomerID, InvoiceNo, InvoiceDate, Revenue].
    snapshot_date : pd.Timestamp, optional
        Reference date for recency / T. Defaults to max(InvoiceDate) + 1 day.

    Returns
    -------
    pd.DataFrame
        One row per customer with all derived features.
    """
    if snapshot_date is None:
        snapshot_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    log.info("Snapshot date: %s", snapshot_date.date())

    inv = _invoice_revenue(df)

    # ------------------------------------------------------------------ #
    # Core RFM per customer
    # ------------------------------------------------------------------ #
    rfm = (
        inv.groupby("CustomerID")
        .agg(
            first_purchase=("invoice_date", "min"),
            last_purchase=("invoice_date", "max"),
            n_invoices=("InvoiceNo", "count"),
            total_revenue=("invoice_revenue", "sum"),
            monetary_value=("invoice_revenue", "mean"),
            purchase_std=("invoice_revenue", "std"),
        )
        .reset_index()
    )

    rfm["recency"] = (snapshot_date - rfm["last_purchase"]).dt.days
    rfm["T"] = (snapshot_date - rfm["first_purchase"]).dt.days
    rfm["days_active"] = (rfm["last_purchase"] - rfm["first_purchase"]).dt.days

    # BG/NBD convention: frequency = n_repeat_transactions = n_invoices - 1
    rfm["frequency"] = (rfm["n_invoices"] - 1).clip(lower=0)

    # Average days between purchases (avoid div/0)
    rfm["avg_days_between_purchases"] = np.where(
        rfm["frequency"] > 0,
        rfm["days_active"] / rfm["frequency"],
        rfm["T"],
    )

    rfm["aov"] = rfm["monetary_value"]  # alias for clarity
    rfm["purchase_std"] = rfm["purchase_std"].fillna(0.0)

    # ------------------------------------------------------------------ #
    # Country (mode per customer)
    # ------------------------------------------------------------------ #
    country_mode = (
        df.groupby("CustomerID")["Country"]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
        .rename(columns={"Country": "country"})
    )
    rfm = rfm.merge(country_mode, on="CustomerID", how="left")

    # ------------------------------------------------------------------ #
    # Filter out customers with < 2 transactions (needed for BG/NBD)
    # ------------------------------------------------------------------ #
    before = len(rfm)
    rfm = rfm[rfm["n_invoices"] >= 2].copy()
    log.info(
        "Filtered customers with < 2 invoices: %d → %d", before, len(rfm)
    )

    # ------------------------------------------------------------------ #
    # Monetary value must be > 0 for Gamma-Gamma
    # ------------------------------------------------------------------ #
    rfm = rfm[rfm["monetary_value"] > 0].copy()

    log.info("RFM table: %d customers", len(rfm))
    log.info("  Recency  — min: %d, median: %d, max: %d days",
             rfm["recency"].min(), rfm["recency"].median(), rfm["recency"].max())
    log.info("  Frequency — min: %d, median: %d, max: %d",
             rfm["frequency"].min(), int(rfm["frequency"].median()), rfm["frequency"].max())
    log.info("  Monetary  — min: £%.2f, median: £%.2f, max: £%.2f",
             rfm["monetary_value"].min(), rfm["monetary_value"].median(), rfm["monetary_value"].max())

    return rfm.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_rfm(rfm: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rfm.to_parquet(RFM_PATH, index=False)
    log.info("Saved RFM features: %s (%d customers)", RFM_PATH, len(rfm))
    return RFM_PATH


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> pd.DataFrame:
    if not TRANSACTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Transactions file not found: {TRANSACTIONS_PATH}\n"
            "Run pipelines/ingest.py first."
        )
    df = pd.read_parquet(TRANSACTIONS_PATH)
    rfm = compute_rfm(df)
    save_rfm(rfm)
    return rfm


if __name__ == "__main__":
    main()
