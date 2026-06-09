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
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from clv_platform.database.connection import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="tenant", cascade="all, delete-orphan")
    predictions = relationship("CustomerClvPrediction", back_populates="tenant", cascade="all, delete-orphan")
    segments = relationship("CustomerSegment", back_populates="tenant", cascade="all, delete-orphan")
    model_runs = relationship("ModelRun", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    webhook_subscriptions = relationship("WebhookSubscription", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # Admin, Analyst, Business User
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    mfa = relationship("UserMfa", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sso = relationship("UserSso", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class UserMfa(Base):
    __tablename__ = "user_mfa"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    secret_key = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    backup_codes = Column(JSON, nullable=True)  # List of hashed recovery codes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mfa")


class UserSso(Base):
    __tablename__ = "user_sso"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # e.g., google, okta
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sso")


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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    tenant = relationship("Tenant", back_populates="customers")
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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    customer = relationship("Customer", back_populates="transactions")
    tenant = relationship("Tenant", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint(
            "invoice_no", "stock_code", "quantity", "price", "invoice_date", "customer_id", "tenant_id",
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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    tenant = relationship("Tenant", back_populates="model_runs")


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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    customer = relationship("Customer", back_populates="predictions")
    tenant = relationship("Tenant", back_populates="predictions")


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
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)

    customer = relationship("Customer", back_populates="segments")
    tenant = relationship("Tenant", back_populates="segments")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    scopes = Column(JSON, nullable=True)  # List of scopes allowed e.g., ["read", "write"]
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(255), nullable=False)  # e.g., "login", "upload_csv", "generate_pdf"
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)  # e.g., "customer.churn_risk_increased", "prediction.completed"
    target_url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="webhook_subscriptions")
    deliveries = relationship("WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSON, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("WebhookSubscription", back_populates="deliveries")

