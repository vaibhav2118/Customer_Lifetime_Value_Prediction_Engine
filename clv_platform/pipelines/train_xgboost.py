import logging
import warnings
import uuid
from pathlib import Path
import joblib
import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from clv_platform.database.connection import SessionLocal
from clv_platform.database.models import ModelRun
from clv_platform.pipelines.features import load_transactions_from_db, compute_rfm

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

XGB_SCORES_PATH = PROCESSED_DIR / "xgb_scores.parquet"
XGB_MODEL_PATH = MODELS_DIR / "xgb_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler_xgb.pkl"

MLFLOW_EXPERIMENT = "CLV_XGBoost_SaaS"
TRAIN_SPLIT_RATIO = 0.75
PREDICTION_DAYS = 180

FEATURE_COLS = [
    "recency", "frequency", "T", "monetary_value",
    "total_revenue", "n_invoices", "purchase_std",
    "days_active", "avg_days_between_purchases",
]

def build_supervised_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Create a supervised CLV dataset using a temporal train/holdout split."""
    min_date = df["invoice_date"].min()
    max_date = df["invoice_date"].max()
    split_date = min_date + (max_date - min_date) * TRAIN_SPLIT_RATIO

    log.info("XGBoost Temporal Split Date: %s (Training Ends Here)", split_date.date())
    df_train = df[df["invoice_date"] < split_date].copy()
    df_hold = df[df["invoice_date"] >= split_date].copy()

    # RFM features on training period
    snapshot_train = split_date
    rfm_train = compute_rfm(df_train, snapshot_date=snapshot_train)

    if rfm_train.empty:
        raise ValueError("RFM features on training slice returned empty dataset.")

    # Holdout revenue per customer
    holdout_rev = (
        df_hold.groupby("customer_id")["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"revenue": "holdout_revenue"})
    )

    # Join
    dataset = rfm_train.merge(holdout_rev, on="customer_id", how="left")
    dataset["holdout_revenue"] = dataset["holdout_revenue"].fillna(0.0)

    log.info("Supervised dataset constructed. Customers: %d. Positive Holdout Spend: %.2f%%",
             len(dataset), 100 * (dataset["holdout_revenue"] > 0).mean())
    return dataset

def train_xgboost(dataset: pd.DataFrame, run_uuid: str):
    """Train XGBRegressor and log to MLflow and database runs."""
    X = dataset[FEATURE_COLS].fillna(0.0)
    y = dataset["holdout_revenue"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    params = dict(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        eval_metric="rmse",
        random_state=42,
        n_jobs=-1,
    )

    # Setup MLflow
    try:
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
    except Exception as e:
        log.warning("Could not set MLflow experiment: %s", e)

    cv_rmse, cv_mae, cv_r2 = [], [], []

    # Cross Validation
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    for fold, (tr_idx, val_idx) in enumerate(kf.split(X_scaled)):
        X_tr, X_val = X_scaled[tr_idx], X_scaled[val_idx]
        y_tr, y_val = y[tr_idx], y[val_idx]

        model_fold = XGBRegressor(**params)
        model_fold.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        preds = model_fold.predict(X_val).clip(min=0)
        
        cv_rmse.append(np.sqrt(mean_squared_error(y_val, preds)))
        cv_mae.append(mean_absolute_error(y_val, preds))
        cv_r2.append(r2_score(y_val, preds))

    mean_rmse = float(np.mean(cv_rmse))
    mean_mae = float(np.mean(cv_mae))
    mean_r2 = float(np.mean(cv_r2))

    log.info("CV Mean RMSE: £%.2f, Mean MAE: £%.2f, Mean R2: %.4f", mean_rmse, mean_mae, mean_r2)

    # Log to MLflow if active
    try:
        with mlflow.start_run(run_name=f"run_{run_uuid[:8]}"):
            mlflow.log_params(params)
            mlflow.log_metric("cv_rmse", mean_rmse)
            mlflow.log_metric("cv_mae", mean_mae)
            mlflow.log_metric("cv_r2", mean_r2)
            
            # Log feature importance chart
            import matplotlib.pyplot as plt
            importances = model_fold.feature_importances_
            fig, ax = plt.subplots(figsize=(8, 5))
            y_pos = np.arange(len(FEATURE_COLS))
            sorted_idx = np.argsort(importances)
            ax.barh(y_pos, importances[sorted_idx], align="center", color="#3182CE")
            ax.set_yticks(y_pos)
            ax.set_yticklabels([FEATURE_COLS[i] for i in sorted_idx])
            ax.set_xlabel("Importance")
            ax.set_title("XGBoost Feature Importances")
            plt.tight_layout()
            
            img_path = PROJECT_ROOT / "outputs" / "reports" / "xgb_feature_importance.png"
            img_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(img_path, dpi=150)
            plt.close(fig)
            mlflow.log_artifact(str(img_path))
    except Exception as e:
        log.warning("Could not log to MLflow: %s", e)

    # Fit final model on full training data
    final_model = XGBRegressor(**params)
    final_model.fit(X_scaled, y, verbose=False)

    # Log to Postgres runs database
    db = SessionLocal()
    try:
        metrics = {
            "cv_rmse": mean_rmse,
            "cv_mae": mean_mae,
            "cv_r2": mean_r2,
            "n_customers": len(dataset),
            "split_ratio": TRAIN_SPLIT_RATIO
        }
        db_run = ModelRun(
            run_uuid=run_uuid,
            model_type="xgboost",
            run_type="train",
            status="success",
            metrics=metrics
        )
        db.add(db_run)
        db.commit()
    except Exception as e:
        log.error("Failed to log XGBoost run to Postgres: %s", e)
    finally:
        db.close()

    return final_model, scaler

def score_all(df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """Score all customers on the full dataset using the trained XGB model."""
    snapshot = df["invoice_date"].max() + pd.Timedelta(days=1)
    rfm_full = compute_rfm(df, snapshot_date=snapshot)

    X = rfm_full[FEATURE_COLS].fillna(0.0)
    X_scaled = scaler.transform(X)
    preds = model.predict(X_scaled).clip(min=0)

    scores = rfm_full[["customer_id"]].copy()
    scores["clv_xgb"] = preds
    return scores

def main() -> pd.DataFrame:
    db = SessionLocal()
    try:
        df_txns = load_transactions_from_db(db)
        if df_txns.empty:
            log.warning("No transactions in database to build dataset. Please ingest data first.")
            return pd.DataFrame()
            
        dataset = build_supervised_dataset(df_txns)
        
        run_uuid = str(uuid.uuid4())
        model, scaler = train_xgboost(dataset, run_uuid)
        
        # score all
        scores = score_all(df_txns, model, scaler)
        
        # Save model and metrics locally
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, XGB_MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
        
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        scores.to_parquet(XGB_SCORES_PATH, index=False)
        
        log.info("XGBoost training pipeline completed successfully.")
        return scores
    finally:
        db.close()

if __name__ == "__main__":
    main()
