import logging
import time
import io
from datetime import datetime
from contextlib import asynccontextmanager
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from clv_platform.database.connection import get_db, init_db, IS_SQLITE
from clv_platform.database.models import User, Customer, Transaction, CustomerClvPrediction, CustomerSegment
from clv_platform.api.schemas import (
    LoginRequest, TokenResponse, ScoreRequest, ScoreResponse, TransactionItem,
    CustomerProfileResponse, CustomerTransactionResponse, TopCustomerResponse,
    OverviewResponse, SegmentBreakdown, HealthResponse
)
from clv_platform.api import predictor
from clv_platform.api.predictor import load_models, get_model_status, predict
from clv_platform.services.auth import (
    verify_password, get_password_hash, create_access_token,
    require_admin, require_analyst_or_above, require_any_user, seed_default_users
)
from clv_platform.services.ingestion import ingest_dataframe_to_db
from clv_platform.services.recommendations import generate_recommendations
from clv_platform.services.reporting import generate_pdf_report, generate_excel_report

__version__ = "2.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("CLV Production Platform v%s starting up...", __version__)
    
    # Initialize DB schema
    init_db()
    
    # Seed base users in database
    db = next(get_db())
    try:
        seed_default_users(db)
        log.info("Database user seeding completed.")
    except Exception as e:
        log.error("Could not seed users: %s", e)
    finally:
        db.close()
        
    # Load ML models
    load_models()
    log.info("API initialized and ready.")
    yield
    log.info("Shutting down CLV API.")

app = FastAPI(
    title="Customer Lifetime Value SaaS Platform API",
    description="SaaS API supporting database connections, security (RBAC/JWT), reporting, and pipelines.",
    version=__version__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health check ---
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health(db: Session = Depends(get_db)):
    db_ok = "degraded"
    try:
        # Check DB
        db.execute(func.now() if not IS_SQLITE else func.time())
        db_ok = "healthy"
    except Exception as e:
        log.warning("Database healthcheck failed: %s", e)

    model_status = get_model_status()
    all_critical = model_status.get("bg_nbd", False) or model_status.get("xgb", False)
    
    return HealthResponse(
        status="ok" if (all_critical and db_ok == "healthy") else "degraded",
        models_loaded=model_status,
        database_status=db_ok,
        version=__version__
    )

# --- JWT Authenticate Route ---
@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Authenticate user
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

# For API documentation testing
@app.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Authentication"], include_in_schema=False)
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

# --- Predictions & Scoring ---
@app.post("/api/v1/predictions/score", response_model=ScoreResponse, tags=["Predictions"])
def score_single(req: ScoreRequest, db: Session = Depends(get_db), current_user = Depends(require_analyst_or_above)):
    try:
        txn_list = [
            {
                "invoice_date": t.invoice_date,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
            }
            for t in req.transactions
        ]
        
        # Calculate prediction using predictor
        result = predict(customer_id=req.customer_id, transactions=txn_list)
        
        # Retrieve or create customer record
        customer = db.query(Customer).filter(Customer.customer_id == req.customer_id).first()
        if not customer:
            customer = Customer(customer_id=req.customer_id, country="Unknown")
            db.add(customer)
            db.commit()
            db.refresh(customer)
            
        # Get recommendations
        rec_details = generate_recommendations(req.customer_id, result["recommendation_tier"], db)
        result["recommendation_details"] = rec_details
        
        # Save to predictions database
        # Remove old prediction if exists
        db.query(CustomerClvPrediction).filter(CustomerClvPrediction.customer_id == req.customer_id).delete()
        
        db_pred = CustomerClvPrediction(
            customer_id=req.customer_id,
            predicted_clv_6months=result["predicted_clv_6months"],
            churn_risk_score=result["churn_risk_score"],
            churn_risk_tier=result["churn_risk_tier"],
            expected_purchases_6m=result["expected_purchases_6m"],
            model_used=result["model_used"],
            recommendation_tier=result["recommendation_tier"],
            recommendation_details=rec_details,
            run_id="api_run"
        )
        db.add(db_pred)
        db.commit()
        
        return ScoreResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        log.error("Scoring error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal scoring error.")

@app.post("/api/v1/predictions/refresh", tags=["Predictions"])
def refresh_all_predictions(db: Session = Depends(get_db), current_user = Depends(require_admin)):
    """Triggers end-to-end predicting/segmenting for database transactions."""
    try:
        from clv_platform.pipelines import segment
        segment.run_segmentation_and_predictions()
        return {"message": "Database predictions refreshed successfully."}
    except Exception as e:
        log.error("Prediction refresh failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

# --- Customer Explorer ---
@app.get("/api/v1/customers/{customer_id}", response_model=CustomerProfileResponse, tags=["Customer Explorer"])
def get_customer_profile(customer_id: str, db: Session = Depends(get_db), current_user = Depends(require_any_user)):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    pred = db.query(CustomerClvPrediction).filter(CustomerClvPrediction.customer_id == customer_id).first()
    
    # Calculate RFM features on the fly
    txns = db.query(Transaction).filter(Transaction.customer_id == customer_id).all()
    
    # Simple aggregates
    txns_data = []
    tot_rev = 0.0
    for t in txns:
        rev = float(t.revenue)
        tot_rev += rev
        txns_data.append(
            CustomerTransactionResponse(
                invoice_no=t.invoice_no,
                stock_code=t.stock_code,
                description=t.description,
                quantity=t.quantity,
                price=float(t.price),
                invoice_date=t.invoice_date,
                revenue=rev
            )
        )
        
    # Sort transactions by date descending
    txns_data.sort(key=lambda x: x.invoice_date, reverse=True)
    
    # Feature calculations
    freq = max(len(txns_data) - 1, 0)
    mon = tot_rev / len(txns_data) if txns_data else 0.0
    rec = 0.0
    
    if txns_data:
        max_date = max(t.invoice_date for t in txns)
        # Convert timezone aware or naive to naive for timedelta compatibility
        ref_date = func.now()
        # Recency days
        rec = float((datetime.now().date() - max_date.date()).days)
        
    return CustomerProfileResponse(
        customer_id=customer.customer_id,
        country=customer.country or "Unknown",
        recency=rec,
        frequency=freq,
        monetary=mon,
        predicted_clv_6months=float(pred.predicted_clv_6months) if pred else None,
        churn_risk_score=float(pred.churn_risk_score) if pred else None,
        churn_risk_tier=pred.churn_risk_tier if pred else None,
        expected_purchases_6m=float(pred.expected_purchases_6m) if pred else None,
        recommendation_tier=pred.recommendation_tier if pred else None,
        recommendation_details=pred.recommendation_details if pred else None,
        transactions=txns_data
    )

@app.get("/api/v1/customers/top-customers", response_model=list[TopCustomerResponse], tags=["Customer Explorer"])
def get_top_clv_customers(limit: int = 100, db: Session = Depends(get_db), current_user = Depends(require_any_user)):
    top = (
        db.query(CustomerClvPrediction)
        .order_by(CustomerClvPrediction.predicted_clv_6months.desc())
        .limit(limit)
        .all()
    )
    
    return [
        TopCustomerResponse(
            customer_id=t.customer_id,
            predicted_clv_6months=float(t.predicted_clv_6months),
            churn_risk_score=float(t.churn_risk_score),
            churn_risk_tier=t.churn_risk_tier,
            recommendation_tier=t.recommendation_tier
        )
        for t in top
    ]

# --- Analytics Page ---
@app.get("/api/v1/analytics/overview", response_model=OverviewResponse, tags=["Analytics"])
def get_overview_analytics(db: Session = Depends(get_db), current_user = Depends(require_any_user)):
    total_customers = db.query(Customer).count()
    if total_customers == 0:
        return OverviewResponse(
            total_customers=0, avg_clv=0.0, total_predicted_revenue=0.0, avg_churn_risk=0.0, segments=[]
        )
        
    clv_stats = db.query(
        func.avg(CustomerClvPrediction.predicted_clv_6months),
        func.sum(CustomerClvPrediction.predicted_clv_6months),
        func.avg(CustomerClvPrediction.churn_risk_score)
    ).first()
    
    avg_clv = float(clv_stats[0]) if clv_stats[0] is not None else 0.0
    total_clv = float(clv_stats[1]) if clv_stats[1] is not None else 0.0
    avg_churn = float(clv_stats[2]) if clv_stats[2] is not None else 0.0
    
    # Segment breakdown counts
    seg_stats = (
        db.query(
            CustomerClvPrediction.recommendation_tier,
            func.count(CustomerClvPrediction.id),
            func.avg(CustomerClvPrediction.predicted_clv_6months)
        )
        .group_by(CustomerClvPrediction.recommendation_tier)
        .all()
    )
    
    segments = []
    for tier, count, avg in seg_stats:
        segments.append(
            SegmentBreakdown(
                segment_name=tier,
                customer_count=count,
                percentage=round((count / total_customers) * 100, 2),
                avg_clv=round(float(avg), 2)
            )
        )
        
    return OverviewResponse(
        total_customers=total_customers,
        avg_clv=round(avg_clv, 2),
        total_predicted_revenue=round(total_clv, 2),
        avg_churn_risk=round(avg_churn, 4),
        segments=segments
    )

# --- Management & Pipelines ---
def background_retrain_runner():
    log.info("Launching background model retraining pipeline...")
    try:
        from clv_platform.pipelines import run_pipeline
        run_pipeline.run_all()
        # Reload models in memory once trained
        load_models()
        log.info("Background retraining complete and models reloaded successfully.")
    except Exception as e:
        log.exception("Failed background retraining: %s", e)

@app.post("/api/v1/management/retrain", tags=["Management"])
def retrain_models(background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user = Depends(require_admin)):
    background_tasks.add_task(background_retrain_runner)
    return {"status": "success", "message": "Model retraining pipeline launched in the background."}

@app.post("/api/v1/management/upload-csv", tags=["Management"])
async def upload_csv_data(file: UploadFile = File(...), db: Session = Depends(get_db), current_user = Depends(require_admin)):
    """Receives transaction CSV file, cleans, validates and loads to DB."""
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Execute Ingestion
        results = ingest_dataframe_to_db(df, db)
        return {
            "status": "success",
            "message": "CSV uploaded and transactions ingested successfully.",
            "metrics": results
        }
    except Exception as e:
        log.error("CSV upload failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Failed to process uploaded CSV: {str(e)}")

# --- Reports & Downloads ---
@app.get("/api/v1/reports/pdf", tags=["Reporting"])
def download_pdf_summary(db: Session = Depends(get_db), current_user = Depends(require_any_user)):
    pdf_buffer = generate_pdf_report(db)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CLV_Executive_Report_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )

@app.get("/api/v1/reports/excel", tags=["Reporting"])
def download_excel_sheets(db: Session = Depends(get_db), current_user = Depends(require_any_user)):
    excel_buffer = generate_excel_report(db)
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=CLV_Customer_Data_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )
