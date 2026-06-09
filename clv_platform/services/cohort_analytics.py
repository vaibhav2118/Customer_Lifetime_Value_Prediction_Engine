import logging
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from clv_platform.database.models import Transaction, Customer

log = logging.getLogger(__name__)

def calculate_cohort_matrix(db: Session, tenant_id: int = None) -> dict:
    """
    Computes a customer retention cohort matrix based on registration/first-purchase month.
    Returns:
        {
            "cohorts": [
                {
                    "cohort_month": "2024-01",
                    "cohort_size": 150,
                    "retention": [100.0, 85.0, 72.0, ...]
                },
                ...
            ]
        }
    """
    query = """
        SELECT customer_id, invoice_date, revenue
        FROM transactions
        WHERE 1=1
    """
    params = {}
    if tenant_id is not None:
        query += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    df = pd.read_sql(text(query), db.bind, params=params)
    if df.empty:
        return {"cohorts": []}

    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["order_month"] = df["invoice_date"].dt.to_period("M")

    # Determine first purchase month per customer
    cohort_df = df.groupby("customer_id")["order_month"].min().reset_index()
    cohort_df.rename(columns={"order_month": "cohort_month"}, inplace=True)

    # Merge back to transactions
    merged = pd.merge(df, cohort_df, on="customer_id")

    # Cohort Index is months between order_month and cohort_month
    merged["cohort_index"] = (merged["order_month"] - merged["cohort_month"]).apply(lambda x: x.n)

    # Group by cohort_month & cohort_index to count unique customers
    cohort_group = merged.groupby(["cohort_month", "cohort_index"])["customer_id"].nunique().reset_index()
    cohort_group.rename(columns={"customer_id": "active_customers"}, inplace=True)

    # Convert period format to string e.g., '2024-01'
    cohort_group["cohort_month"] = cohort_group["cohort_month"].astype(str)

    # Calculate cohort size (Index = 0 count)
    cohort_sizes = cohort_group[cohort_group["cohort_index"] == 0][["cohort_month", "active_customers"]]
    cohort_sizes.rename(columns={"active_customers": "cohort_size"}, inplace=True)

    # Merge back
    final_df = pd.merge(cohort_group, cohort_sizes, on="cohort_month")
    final_df["retention_pct"] = (final_df["active_customers"] / final_df["cohort_size"] * 100).round(2)

    # Pivot to format response
    cohort_list = []
    for cohort_month, group in final_df.groupby("cohort_month"):
        size = int(group["cohort_size"].values[0])
        # Sort by index
        sorted_group = group.sort_values("cohort_index")
        retention_list = []
        max_idx = sorted_group["cohort_index"].max()
        
        # Ensure we have contiguous index values [0, 1, 2...]
        retention_map = {row["cohort_index"]: row["retention_pct"] for _, row in sorted_group.iterrows()}
        for i in range(max_idx + 1):
            retention_list.append(float(retention_map.get(i, 0.0)))
            
        cohort_list.append({
            "cohort_month": cohort_month,
            "cohort_size": size,
            "retention": retention_list
        })

    # Sort cohort list chronologically
    cohort_list.sort(key=lambda x: x["cohort_month"])
    return {"cohorts": cohort_list}

def calculate_cohort_revenue_decay(db: Session, tenant_id: int = None) -> dict:
    """
    Computes cohort total revenue values over subsequent months.
    """
    query = """
        SELECT customer_id, invoice_date, revenue
        FROM transactions
        WHERE 1=1
    """
    params = {}
    if tenant_id is not None:
        query += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    df = pd.read_sql(text(query), db.bind, params=params)
    if df.empty:
        return {"revenue_decay": []}

    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["order_month"] = df["invoice_date"].dt.to_period("M")
    df["revenue"] = df["revenue"].astype(float)

    cohort_df = df.groupby("customer_id")["order_month"].min().reset_index()
    cohort_df.rename(columns={"order_month": "cohort_month"}, inplace=True)

    merged = pd.merge(df, cohort_df, on="customer_id")
    merged["cohort_index"] = (merged["order_month"] - merged["cohort_month"]).apply(lambda x: x.n)

    # Group by cohort_month & cohort_index to sum revenue
    cohort_rev = merged.groupby(["cohort_month", "cohort_index"])["revenue"].sum().reset_index()
    cohort_rev["cohort_month"] = cohort_rev["cohort_month"].astype(str)

    cohort_sizes = merged.groupby("cohort_month")["customer_id"].nunique().reset_index()
    cohort_sizes.rename(columns={"customer_id": "cohort_size"}, inplace=True)
    cohort_sizes["cohort_month"] = cohort_sizes["cohort_month"].astype(str)

    decay_list = []
    for cohort_month, group in cohort_rev.groupby("cohort_month"):
        sorted_group = group.sort_values("cohort_index")
        revenue_list = []
        max_idx = sorted_group["cohort_index"].max()
        
        rev_map = {row["cohort_index"]: row["revenue"] for _, row in sorted_group.iterrows()}
        for i in range(max_idx + 1):
            revenue_list.append(float(round(rev_map.get(i, 0.0), 2)))
            
        size_row = cohort_sizes[cohort_sizes["cohort_month"] == cohort_month]
        size = int(size_row["cohort_size"].values[0]) if not size_row.empty else 0
            
        decay_list.append({
            "cohort_month": cohort_month,
            "cohort_size": size,
            "revenue": revenue_list
        })

    decay_list.sort(key=lambda x: x["cohort_month"])
    return {"revenue_decay": decay_list}
