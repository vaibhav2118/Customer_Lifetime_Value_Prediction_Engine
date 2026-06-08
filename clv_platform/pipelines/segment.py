import logging
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from clv_platform.database.connection import SessionLocal
from clv_platform.database.models import CustomerClvPrediction, CustomerSegment
from clv_platform.services.recommendations import generate_recommendations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

RFM_PATH = PROCESSED_DIR / "rfm_features.parquet"
BG_NBD_SCORES_PATH = PROCESSED_DIR / "bg_nbd_scores.parquet"
XGB_SCORES_PATH = PROCESSED_DIR / "xgb_scores.parquet"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "clv_scores.csv"

KMEANS_MODEL_PATH = MODELS_DIR / "kmeans_model.pkl"
CLV_SCALER_PATH = MODELS_DIR / "clv_scaler.pkl"

PREDICTION_DAYS = 180
BG_NBD_WEIGHT = 0.6
XGB_WEIGHT = 0.4
TIER_ORDER = ["Bronze", "Silver", "Gold", "Platinum"]

def get_churn_tier(score: float) -> str:
    """Map numeric churn probability to Low/Medium/High tier."""
    if score < 0.3:
        return "Low"
    elif score < 0.7:
        return "Medium"
    else:
        return "High"

def run_segmentation_and_predictions():
    # 1. Load scores
    if not BG_NBD_SCORES_PATH.exists() or not XGB_SCORES_PATH.exists():
        raise FileNotFoundError(
            "BG/NBD or XGBoost scores not found in processed cache. Train models first."
        )

    log.info("Loading feature scores...")
    rfm = pd.read_parquet(RFM_PATH)
    bg_scores = pd.read_parquet(BG_NBD_SCORES_PATH)
    xgb_scores = pd.read_parquet(XGB_SCORES_PATH)

    # Merge
    merged = rfm.merge(bg_scores, on="customer_id", how="left")
    merged = merged.merge(xgb_scores, on="customer_id", how="left")
    
    # Fill missing scores
    merged["clv_bg_nbd"] = merged["clv_bg_nbd"].fillna(0.0)
    merged["clv_xgb"] = merged["clv_xgb"].fillna(0.0)
    merged["expected_purchases_6m"] = merged["expected_purchases_6m"].fillna(0.0)
    merged["churn_risk_score"] = merged["churn_risk_score"].fillna(0.5)

    # 2. Ensemble CLV
    # Calculate weighted average CLV
    merged["clv_ensemble"] = (BG_NBD_WEIGHT * merged["clv_bg_nbd"]) + (XGB_WEIGHT * merged["clv_xgb"])
    # If a model failed/is missing, fall back to the available one
    merged.loc[merged["clv_bg_nbd"] == 0.0, "clv_ensemble"] = merged["clv_xgb"]
    merged.loc[merged["clv_xgb"] == 0.0, "clv_ensemble"] = merged["clv_bg_nbd"]
    merged.loc[(merged["clv_bg_nbd"] == 0.0) & (merged["clv_xgb"] == 0.0), "clv_ensemble"] = merged["monetary_value"] * 2.0
    merged["clv_ensemble"] = merged["clv_ensemble"].clip(lower=0.0)

    # 3. K-Means Segment Clustering on Predicted CLV
    log.info("Running K-Means (k=4) customer clustering on predicted CLV...")
    clv_values = merged[["clv_ensemble"]].values
    scaler = StandardScaler()
    clv_scaled = scaler.fit_transform(clv_values)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    kmeans.fit(clv_scaled)

    # Map cluster indices to ordered tiers (Bronze, Silver, Gold, Platinum) by centroids
    centroids = kmeans.cluster_centers_.flatten()
    rank_order = np.argsort(centroids)  # cluster indexes ordered from lowest to highest centroid
    cluster_to_tier = {int(rank_order[i]): TIER_ORDER[i] for i in range(4)}

    merged["cluster"] = kmeans.labels_
    merged["clv_tier"] = merged["cluster"].map(cluster_to_tier)

    # Save scaler and kmeans model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(kmeans, KMEANS_MODEL_PATH)
    joblib.dump(scaler, CLV_SCALER_PATH)

    # 4. Save results to PostgreSQL Database
    db = SessionLocal()
    try:
        log.info("Writing CLV predictions and segments to Database...")
        # Clear old tables to prevent outdated duplicates
        db.query(CustomerClvPrediction).delete()
        db.query(CustomerSegment).delete()
        db.commit()

        preds_to_add = []
        segs_to_add = []

        for _, row in merged.iterrows():
            c_id = str(row["customer_id"])
            clv_val = float(row["clv_ensemble"])
            churn_score = float(row["churn_risk_score"])
            expected_purchases = float(row["expected_purchases_6m"])
            tier = str(row["clv_tier"])
            churn_tier = get_churn_tier(churn_score)

            # Generate business recommendations on-the-fly
            rec_details = generate_recommendations(c_id, tier, db)

            pred = CustomerClvPrediction(
                customer_id=c_id,
                predicted_clv_6months=round(clv_val, 2),
                churn_risk_score=round(min(max(churn_score, 0.0), 1.0), 4),
                churn_risk_tier=churn_tier,
                expected_purchases_6m=round(expected_purchases, 2),
                model_used="bg_nbd + xgboost ensemble",
                recommendation_tier=tier,
                recommendation_details=rec_details,
                run_id="run_latest"
            )
            preds_to_add.append(pred)

            segment = CustomerSegment(
                customer_id=c_id,
                segment_label=int(row["cluster"]),
                segment_name=tier,
                recency=float(row["recency"]),
                frequency=float(row["frequency"]),
                monetary=float(row["monetary_value"]),
                run_id="run_latest"
            )
            segs_to_add.append(segment)

        # Batch insert
        db.bulk_save_objects(preds_to_add)
        db.bulk_save_objects(segs_to_add)
        db.commit()
        log.info("Database predictions update completed. Scored %d customers.", len(merged))

        # Save CSV locally for compatibility / exports
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        merged[["customer_id", "clv_ensemble", "clv_tier", "churn_risk_score"]].to_csv(OUTPUT_CSV, index=False)
        log.info("Local outputs saved: %s", OUTPUT_CSV)

    except Exception as e:
        db.rollback()
        log.error("Failed writing predictions to database: %s", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_segmentation_and_predictions()
