from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import List, Optional

# --- Authentication Schemas ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

# --- Prediction & Scoring Schemas ---
class TransactionItem(BaseModel):
    invoice_date: str = Field(..., description="ISO 8601 Date string (YYYY-MM-DD)")
    quantity: int = Field(..., gt=0, description="Quantity of items purchased")
    unit_price: float = Field(..., gt=0.0, description="Unit price of items (GBP)")

class ScoreRequest(BaseModel):
    customer_id: str
    transactions: List[TransactionItem]

class ScoreResponse(BaseModel):
    customer_id: str
    predicted_clv_6months: float
    churn_risk_score: float
    churn_risk_tier: str
    expected_purchases_6m: float
    model_used: str
    recommendation_tier: str
    recommendation_details: Optional[str] = None
    message: Optional[str] = None

# --- Customer Explorer Schemas ---
class CustomerTransactionResponse(BaseModel):
    invoice_no: str
    stock_code: str
    description: Optional[str]
    quantity: int
    price: float
    invoice_date: datetime
    revenue: float

class CustomerProfileResponse(BaseModel):
    customer_id: str
    country: str
    recency: float
    frequency: float
    monetary: float
    predicted_clv_6months: Optional[float] = None
    churn_risk_score: Optional[float] = None
    churn_risk_tier: Optional[str] = None
    expected_purchases_6m: Optional[float] = None
    recommendation_tier: Optional[str] = None
    recommendation_details: Optional[str] = None
    transactions: List[CustomerTransactionResponse]

# --- Analytics Schemas ---
class TopCustomerResponse(BaseModel):
    customer_id: str
    predicted_clv_6months: float
    churn_risk_score: float
    churn_risk_tier: str
    recommendation_tier: str

class SegmentBreakdown(BaseModel):
    segment_name: str
    customer_count: int
    percentage: float
    avg_clv: float

class OverviewResponse(BaseModel):
    total_customers: int
    avg_clv: float
    total_predicted_revenue: float
    avg_churn_risk: float
    segments: List[SegmentBreakdown]

# --- System Health Schema ---
class HealthResponse(BaseModel):
    status: str
    models_loaded: dict
    database_status: str
    version: str
