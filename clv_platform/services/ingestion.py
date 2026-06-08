import logging
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from clv_platform.database.models import Customer, Transaction

log = logging.getLogger(__name__)

def validate_and_clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and cleans transaction dataframe.
    
    Accepts dataframe and standardizes columns:
    - Customer ID / customer_id
    - Invoice / InvoiceNo / invoice_no
    - StockCode / stock_code
    - Description / description
    - Quantity / quantity
    - Price / UnitPrice / price
    - InvoiceDate / invoice_date
    - Country / country
    """
    df = df.copy()
    
    # Map raw excel columns to standardized names if necessary
    col_mapping = {
        "Customer ID": "customer_id",
        "Invoice": "invoice_no",
        "InvoiceNo": "invoice_no",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "Price": "price",
        "UnitPrice": "price",
        "InvoiceDate": "invoice_date",
        "Country": "country"
    }
    
    # Rename columns based on mapping
    rename_dict = {}
    for col in df.columns:
        for raw, std in col_mapping.items():
            if col.strip().lower() == raw.lower():
                rename_dict[col] = std
                
    df.rename(columns=rename_dict, inplace=True)
    
    # Required columns validation
    required_cols = ["invoice_no", "stock_code", "quantity", "price", "invoice_date", "customer_id"]
    for r_col in required_cols:
        if r_col not in df.columns:
            raise ValueError(f"Missing required column: '{r_col}' (original or mapped). Found: {list(df.columns)}")
            
    # Clean dataset
    # 1. Drop rows with null customer_id or description
    initial_len = len(df)
    df.dropna(subset=["customer_id", "description"], inplace=True)
    
    # 2. Convert Customer ID to string (strip decimal point if read as float)
    df["customer_id"] = df["customer_id"].astype(float).astype(int).astype(str)
    
    # 3. Clean and parse StockCode as string
    df["stock_code"] = df["stock_code"].astype(str).str.strip()
    
    # 4. Remove cancellations/returns (InvoiceNo starts with 'C')
    df["invoice_no"] = df["invoice_no"].astype(str).str.strip()
    df = df[~df["invoice_no"].str.startswith("C", na=False)]
    
    # 5. Filter for quantity > 0 and price > 0
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[(df["quantity"] > 0) & (df["price"] > 0)]
    
    # 6. Parse invoice_date
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    
    # 7. Add revenue column
    df["revenue"] = df["quantity"] * df["price"]
    
    # 8. Clean country mode if missing
    if "country" not in df.columns:
        df["country"] = "Unknown"
    else:
        df["country"] = df["country"].fillna("Unknown").astype(str).str.strip()
        
    log.info("Cleaned dataframe. Filtered from %d rows to %d rows.", initial_len, len(df))
    return df

def ingest_dataframe_to_db(df: pd.DataFrame, db: Session) -> dict:
    """
    Ingests cleaned transactions dataframe to database, performing duplicate checks
    and automatically populating customer objects first.
    """
    # Clean and validate first
    cleaned_df = validate_and_clean_dataframe(df)
    
    if cleaned_df.empty:
        return {"customers_added": 0, "transactions_added": 0, "skipped_duplicates": 0}
    
    customers_added = 0
    transactions_added = 0
    skipped_duplicates = 0
    
    # 1. Populate Customers Table
    unique_custs = cleaned_df[["customer_id", "country"]].drop_duplicates(subset=["customer_id"])
    
    # Get existing customer IDs to prevent duplicate query
    existing_cust_ids = set(r[0] for r in db.query(Customer.customer_id).all())
    
    new_customers = []
    for _, row in unique_custs.iterrows():
        c_id = row["customer_id"]
        if c_id not in existing_cust_ids:
            new_customers.append(Customer(customer_id=c_id, country=row["country"]))
            existing_cust_ids.add(c_id)
            customers_added += 1
            
    if new_customers:
        db.bulk_save_objects(new_customers)
        db.commit()
        
    # 2. Populate Transactions Table (Idempotent loop check)
    # To run this quickly and idempotently, we check duplicates using a composite key
    # We can fetch existing transaction hashes (or check via database query batching)
    # Fetch all transactions to build a lookup hash set.
    # Since we might have lots of transactions, we fetch only for the customers we are updating.
    target_cust_ids = list(cleaned_df["customer_id"].unique())
    
    # Query existing transaction hashes to avoid duplicate attempts
    existing_txns = db.query(
        Transaction.invoice_no, Transaction.stock_code, Transaction.quantity, 
        Transaction.price, Transaction.invoice_date, Transaction.customer_id
    ).filter(Transaction.customer_id.in_(target_cust_ids)).all()
    
    # Construct set of unique keys: (invoice_no, stock_code, quantity, price, invoice_date_iso, customer_id)
    # We use iso string for dates to ensure exact matches without timezone-offset mismatches.
    existing_txn_set = set()
    for t_item in existing_txns:
        # t_item[4] is the datetime object
        dt_str = t_item[4].isoformat() if hasattr(t_item[4], "isoformat") else str(t_item[4])
        existing_txn_set.add((
            str(t_item[0]), 
            str(t_item[1]), 
            int(t_item[2]), 
            float(t_item[3]), 
            dt_str, 
            str(t_item[5])
        ))
        
    new_transactions = []
    
    for _, row in cleaned_df.iterrows():
        dt_str = row["invoice_date"].isoformat()
        txn_key = (
            str(row["invoice_no"]),
            str(row["stock_code"]),
            int(row["quantity"]),
            float(row["price"]),
            dt_str,
            str(row["customer_id"])
        )
        
        if txn_key not in existing_txn_set:
            new_transactions.append(
                Transaction(
                    invoice_no=str(row["invoice_no"]),
                    stock_code=str(row["stock_code"]),
                    description=row["description"],
                    quantity=int(row["quantity"]),
                    price=float(row["price"]),
                    invoice_date=row["invoice_date"],
                    revenue=float(row["revenue"]),
                    customer_id=str(row["customer_id"])
                )
            )
            existing_txn_set.add(txn_key)
            transactions_added += 1
        else:
            skipped_duplicates += 1
            
    if new_transactions:
        db.bulk_save_objects(new_transactions)
        db.commit()
        
    log.info(
        "Ingestion completed. Customers Added: %d, Transactions Added: %d, Skipped Duplicates: %d",
        customers_added, transactions_added, skipped_duplicates
    )
    
    return {
        "customers_added": customers_added,
        "transactions_added": transactions_added,
        "skipped_duplicates": skipped_duplicates
    }
