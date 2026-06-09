import logging
import random
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from clv_platform.database.models import Customer, Transaction, CustomerClvPrediction
from clv_platform.services.ingestion import ingest_dataframe_to_db

log = logging.getLogger(__name__)

def sync_shopify_orders(db: Session, tenant_id: int, shop_url: str, access_token: str) -> dict:
    """
    Simulates fetching recent orders from Shopify API and ingests them into the DB.
    """
    log.info("Connecting to Shopify store %s for Tenant %s...", shop_url, tenant_id)
    
    # Generate mock transaction data simulating Shopify Order payload
    mock_orders = []
    countries = ["United Kingdom", "United States", "Germany", "France", "Canada"]
    customer_pool = [str(random.randint(15000, 20000)) for _ in range(50)]
    descriptions = ["RETRO CHILLI LIGHTS", "RED RETROSPOT CUP", "PLASTICS CUP", "VINTAGE CREAM POSTCARD"]
    
    for i in range(random.randint(20, 50)):
        quantity = random.randint(1, 12)
        price = round(random.uniform(2.5, 45.0), 2)
        mock_orders.append({
            "InvoiceNo": f"SH-{random.randint(100000, 999999)}",
            "StockCode": f"SH-{random.randint(1000, 9999)}",
            "Description": random.choice(descriptions),
            "Quantity": quantity,
            "UnitPrice": price,
            "InvoiceDate": (datetime.now() - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d %H:%M:%S"),
            "Customer ID": random.choice(customer_pool),
            "Country": random.choice(countries)
        })
        
    df = pd.DataFrame(mock_orders)
    
    # Run database ingestion
    metrics = ingest_dataframe_to_db(df, db)
    
    # Set tenant_id for all newly created transactions & customers
    cust_ids = list(df["Customer ID"].unique())
    db.execute(
        text("UPDATE customers SET tenant_id = :tenant_id WHERE customer_id IN :cust_ids AND tenant_id IS NULL"),
        {"tenant_id": tenant_id, "cust_ids": tuple(cust_ids)}
    )
    db.execute(
        text("UPDATE transactions SET tenant_id = :tenant_id WHERE customer_id IN :cust_ids AND tenant_id IS NULL"),
        {"tenant_id": tenant_id, "cust_ids": tuple(cust_ids)}
    )
    db.commit()
    
    return {
        "status": "success",
        "orders_synced": len(mock_orders),
        "database_metrics": metrics
    }

def sync_woocommerce_orders(db: Session, tenant_id: int, site_url: str, consumer_key: str, consumer_secret: str) -> dict:
    """
    Simulates fetching orders from WooCommerce REST API.
    """
    log.info("Connecting to WooCommerce site %s for Tenant %s...", site_url, tenant_id)
    # Similar mock-up execution
    return sync_shopify_orders(db, tenant_id, site_url, "woo-oauth-secret")

def push_hubspot_segments(db: Session, tenant_id: int, portal_id: str, api_key: str) -> dict:
    """
    Simulates pushing top spenders and high churn risk lists to HubSpot Contacts lists.
    """
    log.info("Exporting strategic customer segment tiers to HubSpot CRM %s...", portal_id)
    
    # Find customers to sync
    predictions = (
        db.query(CustomerClvPrediction)
        .filter(
            CustomerClvPrediction.tenant_id == tenant_id,
            CustomerClvPrediction.recommendation_tier.in_(["Platinum", "Gold"])
        )
        .all()
    )
    
    return {
        "status": "success",
        "synced_contacts_count": len(predictions),
        "exported_segments": ["Platinum", "Gold"]
    }

def push_klaviyo_profiles(db: Session, tenant_id: int, api_key: str) -> dict:
    """
    Simulates pushing segments to Klaviyo Lists.
    """
    log.info("Pushing customer profiles and risk levels to Klaviyo dashboard...")
    
    predictions = (
        db.query(CustomerClvPrediction)
        .filter(CustomerClvPrediction.tenant_id == tenant_id)
        .all()
    )
    
    return {
        "status": "success",
        "synced_profiles_count": len(predictions),
        "lists_updated": ["CLV_Platinum", "CLV_At_Risk"]
    }

# SQL text helper used in ingestion
from sqlalchemy import text
