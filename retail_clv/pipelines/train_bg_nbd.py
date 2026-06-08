"""
pipelines/train_bg_nbd.py
--------------------------
Phase 3: BG/NBD + Gamma-Gamma probabilistic CLV modeling.

Trains:
  - BetaGeoFitter (BG/NBD)  → purchase frequency prediction
  - GammaGammaFitter         → monetary value prediction
  - Combines both             → 6-month CLV estimate

Outputs:
  - models/bg_nbd_model.pkl
  - models/gg_model.pkl
  - data/processed/bg_nbd_scores.parquet

Usage:
    python pipelines/train_bg_nbd.py
"""

import logging
import warnings
from pathlib import Path

import joblib
import dill
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

RFM_PATH = PROCESSED_DIR / "rfm_features.parquet"
BG_NBD_SCORES_PATH = PROCESSED_DIR / "bg_nbd_scores.parquet"
BG_NBD_MODEL_PATH = MODELS_DIR / "bg_nbd_model.pkl"
GG_MODEL_PATH = MODELS_DIR / "gg_model.pkl"

PREDICTION_PERIOD_DAYS = 180  # 6 months

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_bg_nbd(rfm: pd.DataFrame):
    """Fit BetaGeoFitter on RFM data."""
    try:
        from lifetimes import BetaGeoFitter
    except ImportError:
        raise ImportError(
            "The 'lifetimes' package is required. Install via: pip install lifetimes"
        )

    log.info("Training BG/NBD model (BetaGeoFitter)…")
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
        "Training Gamma-Gamma model on %d customers with repeat purchases…",
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


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score(rfm: pd.DataFrame, bgf, ggf) -> pd.DataFrame:
    """Generate CLV predictions for all customers."""
    log.info("Scoring %d customers for %d-day horizon…", len(rfm), PREDICTION_PERIOD_DAYS)

    scores = rfm[["CustomerID"]].copy()

    # Expected number of purchases in the next 6 months
    # np.asarray() handles both pandas Series and raw ndarray return types
    # across different lifetimes library versions
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

    # Predicted average transaction value (from GG model for repeat buyers)
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

    # 6-month CLV = expected purchases × expected avg value
    scores["clv_bg_nbd"] = scores["expected_purchases_6m"] * scores["expected_avg_value"]
    scores["clv_bg_nbd"] = scores["clv_bg_nbd"].clip(lower=0.0)

    log.info("CLV (BG/NBD) — median: £%.2f, mean: £%.2f, max: £%.2f",
             scores["clv_bg_nbd"].median(),
             scores["clv_bg_nbd"].mean(),
             scores["clv_bg_nbd"].max())
    return scores


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def save_models(bgf, ggf) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # lifetimes models contain lambda functions that joblib/pickle cannot
    # serialize on Python 3.12 — use dill which handles closures/lambdas
    with open(BG_NBD_MODEL_PATH, "wb") as f:
        dill.dump(bgf, f)
    with open(GG_MODEL_PATH, "wb") as f:
        dill.dump(ggf, f)
    log.info("Saved BG/NBD model: %s", BG_NBD_MODEL_PATH)
    log.info("Saved GG model    : %s", GG_MODEL_PATH)


def load_models():
    """Load persisted BG/NBD and Gamma-Gamma models (used by API predictor)."""
    with open(BG_NBD_MODEL_PATH, "rb") as f:
        bgf = dill.load(f)
    with open(GG_MODEL_PATH, "rb") as f:
        ggf = dill.load(f)
    return bgf, ggf


def save_scores(scores: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(BG_NBD_SCORES_PATH, index=False)
    log.info("Saved BG/NBD scores: %s (%d rows)", BG_NBD_SCORES_PATH, len(scores))
    return BG_NBD_SCORES_PATH


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> pd.DataFrame:
    if not RFM_PATH.exists():
        raise FileNotFoundError(
            f"RFM features not found: {RFM_PATH}\n"
            "Run pipelines/features.py first."
        )

    rfm = pd.read_parquet(RFM_PATH)
    log.info("Loaded %d customers from RFM table.", len(rfm))

    bgf = train_bg_nbd(rfm)
    ggf = train_gamma_gamma(rfm, bgf)
    scores = score(rfm, bgf, ggf)
    save_models(bgf, ggf)
    save_scores(scores)
    return scores


if __name__ == "__main__":
    main()
