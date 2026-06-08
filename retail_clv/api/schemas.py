"""
api/schemas.py
--------------
Pydantic v2 request / response schemas for the CLV scoring API.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class Transaction(BaseModel):
    """A single customer transaction."""

    invoice_date: date = Field(..., description="Date of the invoice (YYYY-MM-DD).")
    quantity: float = Field(..., gt=0, description="Number of items purchased.")
    unit_price: float = Field(..., gt=0, description="Price per item in GBP.")

    @property
    def revenue(self) -> float:
        return self.quantity * self.unit_price


class ScoreRequest(BaseModel):
    """POST /score request body."""

    customer_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the customer.",
        examples=["12345"],
    )
    transactions: list[Transaction] = Field(
        ...,
        min_length=1,
        description="List of historical transactions (at least 1 required).",
    )

    @field_validator("transactions")
    @classmethod
    def sort_transactions(cls, v: list[Transaction]) -> list[Transaction]:
        """Ensure chronological order."""
        return sorted(v, key=lambda t: t.invoice_date)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

ClvTier = Literal["Bronze", "Silver", "Gold", "Platinum", "Insufficient Data"]


class ScoreResponse(BaseModel):
    """POST /score response body."""

    customer_id: str
    predicted_clv_6months: float = Field(
        ..., description="Predicted revenue over next 6 months (GBP)."
    )
    clv_tier: ClvTier = Field(
        ..., description="Customer segment: Bronze / Silver / Gold / Platinum."
    )
    churn_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Probability of customer churning (0=low, 1=high)."
    )
    expected_purchases_6m: float = Field(
        ..., description="Predicted number of purchases in next 6 months."
    )
    model_used: str = Field(
        ..., description="Model(s) used for scoring."
    )
    message: str | None = Field(
        None, description="Optional advisory message (e.g., data quality warnings)."
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    models_loaded: dict[str, bool]
    version: str
