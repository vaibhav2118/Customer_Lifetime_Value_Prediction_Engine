"""
api/main.py
-----------
FastAPI application for the CLV Prediction Engine.

Endpoints:
  GET  /health   — liveness / readiness check
  POST /score    — predict CLV for a single customer

Run locally:
    uvicorn api.main:app --reload --port 8000

Or from the retail_clv directory:
    python -m uvicorn api.main:app --reload
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.predictor import get_model_status, load_models, predict
from api.schemas import HealthResponse, ScoreRequest, ScoreResponse

__version__ = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup."""
    log.info("CLV Prediction Engine v%s — loading models…", __version__)
    load_models()
    log.info("Models loaded. API ready.")
    yield
    log.info("Shutting down CLV API.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CLV Prediction Engine",
    description=(
        "Production-grade Customer Lifetime Value prediction API.\n\n"
        "Uses an ensemble of BG/NBD + Gamma-Gamma (probabilistic) and "
        "XGBoost (ML) models to predict 6-month revenue per customer, "
        "assign CLV tiers, and estimate churn risk."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins in dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware: request timing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health / readiness check",
    tags=["System"],
)
async def health() -> HealthResponse:
    """
    Returns the API health status and which models are loaded.

    - **status**: `ok` if all critical models are loaded, else `degraded`.
    - **models_loaded**: per-model availability flags.
    """
    model_status = get_model_status()
    all_critical = model_status.get("bg_nbd", False) and model_status.get("gamma_gamma", False)
    return HealthResponse(
        status="ok" if all_critical else "degraded",
        models_loaded=model_status,
        version=__version__,
    )


# ---------------------------------------------------------------------------
# Score endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/score",
    response_model=ScoreResponse,
    summary="Predict CLV for a customer",
    tags=["Prediction"],
    status_code=status.HTTP_200_OK,
)
async def score(request: ScoreRequest) -> ScoreResponse:
    """
    Predict the 6-month Customer Lifetime Value for a given customer.

    ### Input
    - **customer_id**: Unique identifier.
    - **transactions**: List of historical transactions with `invoice_date`,
      `quantity`, and `unit_price`.

    ### Output
    - **predicted_clv_6months**: Expected revenue in the next 180 days (GBP).
    - **clv_tier**: One of `Bronze`, `Silver`, `Gold`, `Platinum`.
    - **churn_risk_score**: Probability of churn in [0, 1].
    - **expected_purchases_6m**: Predicted transaction count in next 180 days.
    - **model_used**: Which model(s) contributed to the prediction.

    ### Notes
    - At least 1 transaction is required; BG/NBD works best with 2+ transactions.
    - Dates must be in ISO 8601 format (`YYYY-MM-DD`).
    """
    try:
        txn_list = [
            {
                "invoice_date": t.invoice_date,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
            }
            for t in request.transactions
        ]
        result = predict(customer_id=request.customer_id, transactions=txn_list)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        log.error("Scoring error for customer %s: %s", request.customer_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal scoring error. Check server logs.",
        )

    return ScoreResponse(**result)


# ---------------------------------------------------------------------------
# Batch score endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/score/batch",
    response_model=list[ScoreResponse],
    summary="Batch predict CLV for multiple customers",
    tags=["Prediction"],
)
async def score_batch(requests: list[ScoreRequest]) -> list[ScoreResponse]:
    """
    Score multiple customers in a single request (max 500).

    Each item in the array follows the same schema as `/score`.
    """
    if len(requests) > 500:
        raise HTTPException(
            status_code=422,
            detail="Batch size exceeds maximum of 500 customers per request.",
        )

    results = []
    for req in requests:
        txn_list = [
            {
                "invoice_date": t.invoice_date,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
            }
            for t in req.transactions
        ]
        try:
            result = predict(customer_id=req.customer_id, transactions=txn_list)
            results.append(ScoreResponse(**result))
        except Exception as exc:
            log.warning("Batch scoring failed for %s: %s", req.customer_id, exc)
            results.append(
                ScoreResponse(
                    customer_id=req.customer_id,
                    predicted_clv_6months=0.0,
                    clv_tier="Bronze",
                    churn_risk_score=1.0,
                    expected_purchases_6m=0.0,
                    model_used="error",
                    message=str(exc),
                )
            )
    return results


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )
