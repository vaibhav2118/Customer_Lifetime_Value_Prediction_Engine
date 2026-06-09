from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import List, Optional

# --- Authentication & Signup Schemas ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str
    role: Optional[str] = "Business User"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    tenant_id: Optional[int] = None
    mfa_required: Optional[bool] = False

class MfaVerifyRequest(BaseModel):
    email: str
    code: str

class MfaSetupResponse(BaseModel):
    secret: str
    qr_code_url: str

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

# --- Analytics & Advanced Features Schemas ---
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

class CohortItem(BaseModel):
    cohort_month: str
    cohort_size: int
    retention: List[float]

class CohortResponse(BaseModel):
    cohorts: List[CohortItem]

class CohortRevenueItem(BaseModel):
    cohort_month: str
    cohort_size: int
    revenue: List[float]

class CohortRevenueResponse(BaseModel):
    revenue_decay: List[CohortRevenueItem]

class CustomerJourneyEvent(BaseModel):
    event_name: str
    event_date: str
    description: str
    metric_delta: Optional[float] = None

class CustomerJourneyResponse(BaseModel):
    customer_id: str
    events: List[CustomerJourneyEvent]

class RevenueForecastItem(BaseModel):
    date: str
    historical_revenue: Optional[float] = None
    forecasted_revenue: Optional[float] = None
    confidence_upper: Optional[float] = None
    confidence_lower: Optional[float] = None

class RevenueForecastResponse(BaseModel):
    forecast: List[RevenueForecastItem]

class CampaignRecommendationItem(BaseModel):
    id: str
    title: str
    description: str
    target_tier: str
    estimated_revenue_lift: float
    estimated_cost: float
    action_url: str

class CampaignRecommendationResponse(BaseModel):
    recommendations: List[CampaignRecommendationItem]

class CustomerHealthComponents(BaseModel):
    retention_reliability: float
    purchase_frequency: float
    recency_activity: float
    clv_value_index: float

class CustomerHealthResponse(BaseModel):
    customer_id: str
    health_score: float
    label: str
    color: str
    components: CustomerHealthComponents

# --- Enterprise & Infrastructure Schemas ---
class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: Optional[List[str]] = ["read"]
    expires_in_days: Optional[int] = 30

class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: Optional[List[str]]
    created_at: datetime
    expires_at: Optional[datetime]
    token: Optional[str] = None  # Populated only on creation

class AuditLogResponse(BaseModel):
    id: int
    user_email: Optional[str]
    action: str
    ip_address: Optional[str]
    details: Optional[str]
    created_at: datetime

class WebhookSubscriptionRequest(BaseModel):
    event_type: str
    target_url: str

class WebhookSubscriptionResponse(BaseModel):
    id: int
    event_type: str
    target_url: str
    secret: str
    is_active: bool
    created_at: datetime

class ConnectorSyncRequest(BaseModel):
    shop_url: str
    access_token: str

class ConnectorSyncResponse(BaseModel):
    status: str
    orders_synced: int
    message: str

# --- System Health Schema ---
class HealthResponse(BaseModel):
    status: str
    models_loaded: dict
    database_status: str
    version: str

