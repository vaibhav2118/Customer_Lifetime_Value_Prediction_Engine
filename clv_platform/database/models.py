import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from clv_platform.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # Admin, Analyst, Business User
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    country = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    predictions = relationship("CustomerClvPrediction", back_populates="customer", cascade="all, delete-orphan")
    segments = relationship("CustomerSegment", back_populates="customer", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String(50), nullable=False)
    stock_code = Column(String(50), nullable=False)
    description = Column(String(255))
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False, index=True)
    revenue = Column(Numeric(12, 2), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)

    customer = relationship("Customer", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint(
            "invoice_no", "stock_code", "quantity", "price", "invoice_date", "customer_id",
            name="uq_transaction"
        ),
    )


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_uuid = Column(String(100), unique=True, nullable=False, index=True)
    model_type = Column(String(100), nullable=False)  # bg_nbd, xgboost, ensemble
    run_type = Column(String(50), nullable=False)  # train, retrain, predict
    status = Column(String(50), nullable=False)  # running, success, failed
    metrics = Column(JSON, nullable=True)  # JSON holding dict of metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CustomerClvPrediction(Base):
    __tablename__ = "customer_clv_predictions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_clv_6months = Column(Numeric(12, 2), nullable=False)
    churn_risk_score = Column(Float, nullable=False)
    churn_risk_tier = Column(String(20), nullable=False)  # Low, Medium, High
    expected_purchases_6m = Column(Numeric(10, 2), nullable=False)
    model_used = Column(String(100), nullable=False)
    recommendation_tier = Column(String(50), nullable=False)  # Bronze, Silver, Gold, Platinum
    recommendation_details = Column(Text)
    run_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="predictions")


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    segment_label = Column(Integer, nullable=False)  # Cluster ID (0,1,2,3)
    segment_name = Column(String(50), nullable=False)  # Bronze, Silver, Gold, Platinum
    recency = Column(Numeric(10, 2))
    frequency = Column(Numeric(10, 2))
    monetary = Column(Numeric(12, 2))
    run_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="segments")
