import logging
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from clv_platform.database.connection import SessionLocal
from clv_platform.database.models import Transaction, Customer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RFM_PATH = PROCESSED_DIR / "rfm_features.parquet"

def _invoice_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per (customer_id, invoice_no) with invoice_date + revenue."""
    return (
        df.groupby(["customer_id", "invoice_no"])
        .agg(
            invoice_date=("invoice_date", "min"),
            invoice_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

def compute_rfm(df: pd.DataFrame, snapshot_date: pd.Timestamp = None) -> pd.DataFrame:
    """
    Compute RFM and extended features from transactions dataframe.
    """
    if df.empty:
        log.warning("Empty transactions dataframe passed to compute_rfm.")
        return pd.DataFrame()

    if snapshot_date is None:
        # standard snapshot date is max invoice_date + 1 day
        snapshot_date = df["invoice_date"].max() + pd.Timedelta(days=1)
    log.info("Snapshot date for feature calculation: %s", snapshot_date.date())

    inv = _invoice_revenue(df)

    # Core RFM
    rfm = (
        inv.groupby("customer_id")
        .agg(
            first_purchase=("invoice_date", "min"),
            last_purchase=("invoice_date", "max"),
            n_invoices=("invoice_no", "count"),
            total_revenue=("invoice_revenue", "sum"),
            monetary_value=("invoice_revenue", "mean"),
            purchase_std=("invoice_revenue", "std"),
        )
        .reset_index()
    )

    rfm["recency"] = (snapshot_date - rfm["last_purchase"]).dt.days
    rfm["T"] = (snapshot_date - rfm["first_purchase"]).dt.days
    rfm["days_active"] = (rfm["last_purchase"] - rfm["first_purchase"]).dt.days
    
    # BG/NBD: frequency is repeat purchases (invoices - 1)
    rfm["frequency"] = (rfm["n_invoices"] - 1).clip(lower=0)

    # Average days between purchases
    rfm["avg_days_between_purchases"] = np.where(
        rfm["frequency"] > 0,
        rfm["days_active"] / rfm["frequency"],
        rfm["T"]
    )

    rfm["aov"] = rfm["monetary_value"]
    rfm["purchase_std"] = rfm["purchase_std"].fillna(0.0)

    # Country mapping (mode country per customer)
    # Join with customers country
    db = SessionLocal()
    try:
        custs = db.query(Customer.customer_id, Customer.country).all()
        cust_df = pd.DataFrame(custs, columns=["customer_id", "country"])
        rfm = rfm.merge(cust_df, on="customer_id", how="left")
    finally:
        db.close()

    # Filter rules for BG/NBD modeling (minimum 2 transactions, positive revenue)
    before = len(rfm)
    rfm = rfm[rfm["n_invoices"] >= 2].copy()
    rfm = rfm[rfm["monetary_value"] > 0].copy()
    
    log.info("Filtered for model eligibility: %d -> %d customers", before, len(rfm))
    return rfm.reset_index(drop=True)

def load_transactions_from_db(db: Session) -> pd.DataFrame:
    """Load all transaction records from DB into a DataFrame."""
    txns = db.query(
        Transaction.customer_id,
        Transaction.invoice_no,
        Transaction.invoice_date,
        Transaction.revenue
    ).all()
    
    df = pd.DataFrame(txns, columns=["customer_id", "invoice_no", "invoice_date", "revenue"])
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["revenue"] = df["revenue"].astype(float)
    return df

def main() -> pd.DataFrame:
    db = SessionLocal()
    try:
        df_txns = load_transactions_from_db(db)
        if df_txns.empty:
            log.warning("No transactions found in database to extract features. Please ingest data first.")
            return pd.DataFrame()
        
        rfm = compute_rfm(df_txns)
        
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        rfm.to_parquet(RFM_PATH, index=False)
        log.info("Saved features to Parquet cache: %s (%d customers)", RFM_PATH, len(rfm))
        return rfm
    finally:
        db.close()

if __name__ == "__main__":
    main()
