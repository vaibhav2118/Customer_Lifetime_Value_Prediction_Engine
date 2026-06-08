"""
pipelines/train_xgboost.py
--------------------------
Phase 4: XGBoost CLV regression with MLflow experiment tracking.

Approach:
  - Time-split the transaction data:
      Training period  : first 75% of time range
      Holdout period   : last 25% of time range (acts as "future")
  - For each customer active in training:
      Features  = RFM computed on training period
      Label     = actual total revenue in the holdout period (0 if none)
  - Train XGBRegressor with cross-validation, log to MLflow.

Outputs:
  - models/xgb_model.pkl
  - models/scaler_xgb.pkl
  - data/processed/xgb_scores.parquet

MLflow experiment: "CLV_XGBoost"

Usage:
    python pipelines/train_xgboost.py
"""

import logging
import warnings
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

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

TRANSACTIONS_PATH = PROCESSED_DIR / "transactions.parquet"
XGB_SCORES_PATH = PROCESSED_DIR / "xgb_scores.parquet"
XGB_MODEL_PATH = MODELS_DIR / "xgb_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler_xgb.pkl"

MLFLOW_EXPERIMENT = "CLV_XGBoost"
TRAIN_SPLIT_RATIO = 0.75   # 75% of time range → training
PREDICTION_DAYS = 180       # label = revenue in holdout mapped to 6-month window

FEATURE_COLS = [
    "recency", "frequency", "T", "monetary_value",
    "total_revenue", "n_invoices", "purchase_std",
    "days_active", "avg_days_between_purchases",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Time-split dataset builder
# ---------------------------------------------------------------------------

def build_supervised_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a supervised CLV dataset using a temporal train/holdout split.

    Returns a DataFrame with RFM features + label (holdout_revenue).
    """
    min_date = df["InvoiceDate"].min()
    max_date = df["InvoiceDate"].max()
    split_date = min_date + (max_date - min_date) * TRAIN_SPLIT_RATIO

    log.info("Date range   : %s → %s", min_date.date(), max_date.date())
    log.info("Split date   : %s (training ends here)", split_date.date())
    log.info("Holdout range: %s → %s", split_date.date(), max_date.date())

    df_train = df[df["InvoiceDate"] < split_date].copy()
    df_hold = df[df["InvoiceDate"] >= split_date].copy()

    # RFM on training period
    snapshot_train = split_date
    from pipelines.features import compute_rfm
    rfm_train = compute_rfm(df_train, snapshot_date=snapshot_train)

    # Holdout revenue per customer
    holdout_rev = (
        df_hold.groupby("CustomerID")["Revenue"]
        .sum()
        .reset_index()
        .rename(columns={"Revenue": "holdout_revenue"})
    )

    # Join — customers not present in holdout get label = 0
    dataset = rfm_train.merge(holdout_rev, on="CustomerID", how="left")
    dataset["holdout_revenue"] = dataset["holdout_revenue"].fillna(0.0)

    log.info(
        "Supervised dataset: %d customers, label mean=£%.2f, non-zero=%.1f%%",
        len(dataset),
        dataset["holdout_revenue"].mean(),
        100 * (dataset["holdout_revenue"] > 0).mean(),
    )
    return dataset


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_xgboost(dataset: pd.DataFrame):
    """Train XGBRegressor with cross-validation and log to MLflow."""

    X = dataset[FEATURE_COLS].fillna(0.0)
    y = dataset["holdout_revenue"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Hyperparameters
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

    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    with mlflow.start_run(run_name="xgboost_clv") as run:
        log.info("MLflow run ID: %s", run.info.run_id)

        # Log hyperparameters
        mlflow.log_params(params)
        mlflow.log_param("train_split_ratio", TRAIN_SPLIT_RATIO)
        mlflow.log_param("n_features", len(FEATURE_COLS))
        mlflow.log_param("n_customers", len(dataset))

        # Cross-validation metrics
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_rmse, cv_mae, cv_r2 = [], [], []

        for fold, (tr_idx, val_idx) in enumerate(kf.split(X_scaled)):
            X_tr, X_val = X_scaled[tr_idx], X_scaled[val_idx]
            y_tr, y_val = y[tr_idx], y[val_idx]

            model_fold = XGBRegressor(**params)
            model_fold.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )
            preds = model_fold.predict(X_val).clip(min=0)
            cv_rmse.append(np.sqrt(mean_squared_error(y_val, preds)))
            cv_mae.append(mean_absolute_error(y_val, preds))
            cv_r2.append(r2_score(y_val, preds))

        mean_rmse = np.mean(cv_rmse)
        mean_mae = np.mean(cv_mae)
        mean_r2 = np.mean(cv_r2)

        log.info("CV  RMSE : £%.2f (±%.2f)", mean_rmse, np.std(cv_rmse))
        log.info("CV  MAE  : £%.2f (±%.2f)", mean_mae, np.std(cv_mae))
        log.info("CV  R²   : %.4f (±%.4f)", mean_r2, np.std(cv_r2))

        mlflow.log_metric("cv_rmse", mean_rmse)
        mlflow.log_metric("cv_mae", mean_mae)
        mlflow.log_metric("cv_r2", mean_r2)

        # Final model on full training data
        final_model = XGBRegressor(**params)
        final_model.fit(X_scaled, y, verbose=False)

        # Log model to MLflow
        mlflow.xgboost.log_model(final_model, artifact_path="xgb_model")

        # Feature importance plot
        _log_feature_importance(final_model, run)

        log.info("MLflow experiment '%s' — run logged.", MLFLOW_EXPERIMENT)

    return final_model, scaler


def _log_feature_importance(model, run) -> None:
    """Save feature importance chart as MLflow artifact."""
    try:
        import matplotlib.pyplot as plt

        importances = model.feature_importances_
        fig, ax = plt.subplots(figsize=(8, 5))
        y_pos = np.arange(len(FEATURE_COLS))
        sorted_idx = np.argsort(importances)
        ax.barh(y_pos, importances[sorted_idx], align="center", color="#4f8ef7")
        ax.set_yticks(y_pos)
        ax.set_yticklabels([FEATURE_COLS[i] for i in sorted_idx])
        ax.set_xlabel("Importance (gain)")
        ax.set_title("XGBoost Feature Importances — CLV Regression")
        plt.tight_layout()

        img_path = PROJECT_ROOT / "outputs" / "reports" / "xgb_feature_importance.png"
        img_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(img_path, dpi=150)
        plt.close(fig)

        mlflow.log_artifact(str(img_path))
        log.info("Feature importance plot saved: %s", img_path)
    except Exception as exc:
        log.warning("Could not save feature importance plot: %s", exc)


# ---------------------------------------------------------------------------
# Full-corpus scoring
# ---------------------------------------------------------------------------

def score_all(df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """Score all customers on the full dataset using the trained XGB model."""
    from pipelines.features import compute_rfm

    snapshot = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    rfm_full = compute_rfm(df, snapshot_date=snapshot)

    X = rfm_full[FEATURE_COLS].fillna(0.0)
    X_scaled = scaler.transform(X)
    preds = model.predict(X_scaled).clip(min=0)

    scores = rfm_full[["CustomerID"]].copy()
    scores["clv_xgb"] = preds
    log.info(
        "XGB scores — median: £%.2f, mean: £%.2f, max: £%.2f",
        np.median(preds), np.mean(preds), np.max(preds),
    )
    return scores


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def save_models(model, scaler) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, XGB_MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    log.info("Saved XGB model : %s", XGB_MODEL_PATH)
    log.info("Saved XGB scaler: %s", SCALER_PATH)


def save_scores(scores: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(XGB_SCORES_PATH, index=False)
    log.info("Saved XGB scores: %s (%d rows)", XGB_SCORES_PATH, len(scores))
    return XGB_SCORES_PATH


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> pd.DataFrame:
    if not TRANSACTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Transactions file not found: {TRANSACTIONS_PATH}\n"
            "Run pipelines/ingest.py first."
        )

    df = pd.read_parquet(TRANSACTIONS_PATH)
    log.info("Loaded %d transaction rows.", len(df))

    dataset = build_supervised_dataset(df)
    model, scaler = train_xgboost(dataset)
    scores = score_all(df, model, scaler)
    save_models(model, scaler)
    save_scores(scores)
    return scores


if __name__ == "__main__":
    main()
