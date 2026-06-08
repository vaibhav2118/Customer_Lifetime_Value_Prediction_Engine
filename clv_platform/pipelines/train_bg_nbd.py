import logging
import warnings
import uuid
from pathlib import Path
import dill
import numpy as np
import pandas as pd
from clv_platform.database.connection import SessionLocal
from clv_platform.database.models import ModelRun

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

RFM_PATH = PROCESSED_DIR / "rfm_features.parquet"
BG_NBD_SCORES_PATH = PROCESSED_DIR / "bg_nbd_scores.parquet"
BG_NBD_MODEL_PATH = MODELS_DIR / "bg_nbd_model.pkl"
GG_MODEL_PATH = MODELS_DIR / "gg_model.pkl"

PREDICTION_PERIOD_DAYS = 180  # 6 months

def train_bg_nbd(rfm: pd.DataFrame):
    """Fit BetaGeoFitter on RFM data."""
    try:
        from lifetimes import BetaGeoFitter
    except ImportError:
        raise ImportError(
            "The 'lifetimes' package is required. Install via: pip install lifetimes"
        )

    log.info("Training BG/NBD model (BetaGeoFitter)...")
    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(
        frequency=rfm["frequency"],
        recency=rfm["recency"],
        T=rfm["T"],
        verbose=True,
    )
    log.info("BG/NBD params — r=%.4f, alpha=%.4f, a=%.4f, b=%.4f",
             bgf.params_["r"], bgf.params_["alpha"],
             bgf.params_["a"], bgf.params_["b"])
    return bgf

def train_gamma_gamma(rfm: pd.DataFrame, bgf):
    """Fit GammaGammaFitter on customers with repeat purchases."""
    try:
        from lifetimes import GammaGammaFitter
    except ImportError:
        raise ImportError("The 'lifetimes' package is required.")

    # GG model requires customers with at least 1 repeat purchase
    repeat_mask = rfm["frequency"] > 0
    rfm_gg = rfm[repeat_mask].copy()
    log.info(
        "Training Gamma-Gamma model on %d customers with repeat purchases...",
        len(rfm_gg),
    )

    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(
        frequency=rfm_gg["frequency"],
        monetary_value=rfm_gg["monetary_value"],
    )
    log.info(
        "GG params — p=%.4f, q=%.4f, v=%.4f",
        ggf.params_["p"], ggf.params_["q"], ggf.params_["v"],
    )
    return ggf

def score(rfm: pd.DataFrame, bgf, ggf) -> pd.DataFrame:
    """Generate CLV predictions for all customers."""
    log.info("Scoring %d customers for %d-day horizon...", len(rfm), PREDICTION_PERIOD_DAYS)

    scores = rfm[["customer_id"]].copy()

    # Expected number of purchases in the next 6 months
    scores["expected_purchases_6m"] = np.asarray(
        bgf.conditional_expected_number_of_purchases_up_to_time(
            t=PREDICTION_PERIOD_DAYS,
            frequency=rfm["frequency"],
            recency=rfm["recency"],
            T=rfm["T"],
        )
    )

    # Probability customer is still alive (active)
    scores["prob_alive"] = np.asarray(
        bgf.conditional_probability_alive(
            frequency=rfm["frequency"],
            recency=rfm["recency"],
            T=rfm["T"],
        )
    )

    # Churn risk = 1 - P(alive)
    scores["churn_risk_score"] = 1.0 - scores["prob_alive"]

    # Predicted average transaction value
    repeat_mask = rfm["frequency"] > 0
    scores["expected_avg_value"] = rfm["monetary_value"].values  # fallback: actual mean

    if repeat_mask.any():
        rfm_repeat = rfm[repeat_mask]
        predicted_avg = np.asarray(
            ggf.conditional_expected_average_profit(
                frequency=rfm_repeat["frequency"],
                monetary_value=rfm_repeat["monetary_value"],
            )
        )
        scores.loc[repeat_mask.values, "expected_avg_value"] = predicted_avg

    # 6-month CLV = expected purchases * expected avg value
    scores["clv_bg_nbd"] = scores["expected_purchases_6m"] * scores["expected_avg_value"]
    scores["clv_bg_nbd"] = scores["clv_bg_nbd"].clip(lower=0.0)

    log.info("CLV (BG/NBD) — median: £%.2f, mean: £%.2f, max: £%.2f",
             scores["clv_bg_nbd"].median(),
             scores["clv_bg_nbd"].mean(),
             scores["clv_bg_nbd"].max())
    return scores

def save_models(bgf, ggf) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(BG_NBD_MODEL_PATH, "wb") as f:
        dill.dump(bgf, f)
    with open(GG_MODEL_PATH, "wb") as f:
        dill.dump(ggf, f)
    log.info("Saved BG/NBD model: %s", BG_NBD_MODEL_PATH)
    log.info("Saved GG model: %s", GG_MODEL_PATH)

def log_run_to_db(run_uuid: str, bg_params: dict, gg_params: dict):
    db = SessionLocal()
    try:
        metrics = {
            "bg_nbd_params": bg_params,
            "gamma_gamma_params": gg_params
        }
        db_run = ModelRun(
            run_uuid=run_uuid,
            model_type="bg_nbd_gamma_gamma",
            run_type="train",
            status="success",
            metrics=metrics
        )
        db.add(db_run)
        db.commit()
        log.info("Logged BG/NBD model run successfully to PostgreSQL DB: run_uuid=%s", run_uuid)
    except Exception as e:
        log.error("Failed to log model run to DB: %s", e)
    finally:
        db.close()

def main(run_type="train") -> pd.DataFrame:
    if not RFM_PATH.exists():
        log.info("Parquet features not found. Extracting features first...")
        from clv_platform.pipelines import features
        features.main()

    rfm = pd.read_parquet(RFM_PATH)
    log.info("Loaded %d customers from RFM table.", len(rfm))

    run_uuid = str(uuid.uuid4())
    bgf = train_bg_nbd(rfm)
    ggf = train_gamma_gamma(rfm, bgf)
    scores = score(rfm, bgf, ggf)
    save_models(bgf, ggf)
    
    # Save scores
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(BG_NBD_SCORES_PATH, index=False)
    
    # Log database
    bg_params = {k: float(v) for k, v in bgf.params_.items()}
    gg_params = {k: float(v) for k, v in ggf.params_.items()}
    log_run_to_db(run_uuid, bg_params, gg_params)
    
    return scores

if __name__ == "__main__":
    main()
