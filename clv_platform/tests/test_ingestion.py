import pytest
import pandas as pd
from datetime import datetime
from clv_platform.services.ingestion import validate_and_clean_dataframe, ingest_dataframe_to_db
from clv_platform.database.models import Customer, Transaction

def test_validate_and_clean_dataframe():
    # Construct a raw dataframe with typical UCI features, including messy/invalid data
    raw_data = {
        "Customer ID": [12345, 12345, 67890, None, 12345],
        "Invoice": ["536365", "536365", "C536379", "536380", "536381"], # one return (starts with C)
        "StockCode": ["85123A", "71053", "D", "82484", "22752"],
        "Description": ["WHITE HEART", "WHITE METAL", "Discount", "WOODEN STAR", None], # one null description
        "Quantity": [6, -1, 5, 9, 10], # one negative quantity (should be removed or canceller)
        "Price": [2.55, 3.39, 27.50, 0.00, 1.85], # one zero price
        "InvoiceDate": ["2010-12-01 08:26:00", "2010-12-01 08:26:00", "2010-12-01 09:41:00", "2010-12-01 09:41:00", "2010-12-01 09:45:00"],
        "Country": ["United Kingdom", "United Kingdom", "United Kingdom", "United Kingdom", "France"]
    }
    df = pd.DataFrame(raw_data)
    
    cleaned_df = validate_and_clean_dataframe(df)
    
    # Expected results after cleaning:
    # Row 0: Valid. (Customer ID 12345, Quantity 6, Price 2.55) -> Keep
    # Row 1: Quantity -1 <= 0 -> Filtered out
    # Row 2: Invoice starts with C -> Filtered out
    # Row 3: Customer ID is Null -> Filtered out (dropped on subset)
    # Row 4: Description is Null -> Filtered out (dropped on subset)
    # Only Row 0 should remain
    assert len(cleaned_df) == 1
    assert cleaned_df.iloc[0]["customer_id"] == "12345"
    assert cleaned_df.iloc[0]["revenue"] == 6 * 2.55
    assert cleaned_df.iloc[0]["country"] == "United Kingdom"

def test_ingest_dataframe_to_db(db_session):
    raw_data = {
        "Customer ID": [11111, 11111, 22222],
        "InvoiceNo": ["100001", "100001", "100002"],
        "StockCode": ["A", "B", "C"],
        "Description": ["Item A", "Item B", "Item C"],
        "Quantity": [1, 2, 3],
        "UnitPrice": [10.0, 20.0, 30.0],
        "InvoiceDate": ["2026-06-08 10:00:00", "2026-06-08 10:00:00", "2026-06-08 11:00:00"],
        "Country": ["Germany", "Germany", "France"]
    }
    df = pd.DataFrame(raw_data)
    
    # 1. Run first ingestion
    res1 = ingest_dataframe_to_db(df, db_session)
    assert res1["customers_added"] == 2
    assert res1["transactions_added"] == 3
    assert res1["skipped_duplicates"] == 0
    
    # Verify records in database
    custs = db_session.query(Customer).filter(Customer.customer_id.in_(["11111", "22222"])).all()
    assert len(custs) == 2
    txns = db_session.query(Transaction).filter(Transaction.customer_id.in_(["11111", "22222"])).all()
    assert len(txns) == 3
    
    # 2. Run second ingestion with duplicate rows and one new transaction
    raw_data_2 = {
        "Customer ID": [11111, 33333], # 11111 is duplicate transaction, 33333 is new
        "InvoiceNo": ["100001", "100003"],
        "StockCode": ["A", "D"],
        "Description": ["Item A", "Item D"],
        "Quantity": [1, 5],
        "UnitPrice": [10.0, 15.0],
        "InvoiceDate": ["2026-06-08 10:00:00", "2026-06-08 12:00:00"],
        "Country": ["Germany", "Spain"]
    }
    df2 = pd.DataFrame(raw_data_2)
    
    res2 = ingest_dataframe_to_db(df2, db_session)
    # Should skip 11111 (duplicate) and add 33333 (new)
    assert res2["customers_added"] == 1 # 33333
    assert res2["transactions_added"] == 1 # 33333's transaction
    assert res2["skipped_duplicates"] == 1 # 11111's transaction
    
    # Cleanup database
    db_session.query(Transaction).filter(Transaction.customer_id.in_(["11111", "22222", "33333"])).delete()
    db_session.query(Customer).filter(Customer.customer_id.in_(["11111", "22222", "33333"])).delete()
    db_session.commit()
