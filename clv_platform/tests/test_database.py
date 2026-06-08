import pytest
from datetime import datetime
from sqlalchemy import text
from clv_platform.database.models import User, Customer, Transaction, CustomerClvPrediction, CustomerSegment
from sqlalchemy.exc import IntegrityError

def test_database_tables_exist(db_session):
    # Retrieve lists of table names fromsqlite database
    result = db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result.fetchall()]
    
    assert "users" in tables
    assert "customers" in tables
    assert "transactions" in tables
    assert "model_runs" in tables
    assert "customer_clv_predictions" in tables
    assert "customer_segments" in tables

def test_create_and_query_user(db_session):
    # Test user creation
    new_user = User(email="test_analyst@clv.com", hashed_password="hashedpassword123", role="Analyst")
    db_session.add(new_user)
    db_session.commit()
    
    user = db_session.query(User).filter(User.email == "test_analyst@clv.com").first()
    assert user is not None
    assert user.role == "Analyst"
    
    # Cleanup
    db_session.delete(user)
    db_session.commit()

def test_customer_transaction_relationship(db_session):
    # Test customer and transactions relationships
    cust = Customer(customer_id="99999", country="United Kingdom")
    db_session.add(cust)
    db_session.commit()
    
    txn1 = Transaction(
        invoice_no="555555",
        stock_code="85123A",
        description="WHITE HANGING HEART T-LIGHT HOLDER",
        quantity=6,
        price=2.55,
        invoice_date=datetime(2026, 6, 8, 12, 0, 0),
        revenue=15.30,
        customer_id="99999"
    )
    db_session.add(txn1)
    db_session.commit()
    
    # Query customer and verify relationship
    queried_cust = db_session.query(Customer).filter(Customer.customer_id == "99999").first()
    assert queried_cust is not None
    assert len(queried_cust.transactions) == 1
    assert queried_cust.transactions[0].invoice_no == "555555"
    assert float(queried_cust.transactions[0].revenue) == 15.30
    
    # Cleanup (cascade delete should remove the transaction)
    db_session.delete(queried_cust)
    db_session.commit()
    
    orphaned_txn = db_session.query(Transaction).filter(Transaction.customer_id == "99999").first()
    assert orphaned_txn is None

def test_transaction_unique_constraint(db_session):
    # Verify idempotency constraint on transactions
    cust = Customer(customer_id="88888", country="France")
    db_session.add(cust)
    db_session.commit()
    
    txn_kwargs = {
        "invoice_no": "666666",
        "stock_code": "22720",
        "description": "SET OF 3 CAKE TINS PANTRY DESIGN",
        "quantity": 2,
        "price": 4.95,
        "invoice_date": datetime(2026, 6, 8, 14, 0, 0),
        "revenue": 9.90,
        "customer_id": "88888"
    }
    
    txn1 = Transaction(**txn_kwargs)
    db_session.add(txn1)
    db_session.commit()
    
    # Try inserting duplicate transaction
    txn2 = Transaction(**txn_kwargs)
    db_session.add(txn2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    
    # Cleanup
    db_session.delete(cust)
    db_session.commit()
