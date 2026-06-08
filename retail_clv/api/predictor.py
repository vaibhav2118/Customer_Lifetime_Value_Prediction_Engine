"""
api/predictor.py
----------------
Model loading and inference logic for the CLV scoring API.

Loads BG/NBD, Gamma-Gamma, XGBoost, K-Means models at startup and
exposes a single `predict()` function that accepts a list of transactions
and returns a scored result dict.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import dill
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

PREDICTION_DAYS = 180  # 6 months
BG_NBD_WEIGHT = 0.6
XGB_WEIGHT = 0.4

# CLV thresholds for tier assignment (trained model centroids take precedence)
_TIER_FALLBACK_PERCENTILES = [0, 25, 50, 75, 100]  # Bronze/Silver/Gold/Platinum


class ModelRegistry:
    """Lazy-loading model registry — loads models once on first use."""

    def __init__(self):
        self._bgf = None
        self._ggf = None
        self._xgb = None
        self._xgb_scaler = None
        self._kmeans = None
        self._clv_scaler = None
        self._loaded: dict[str, bool] = {}

    def _try_load(self, name: str, path: Path, use_dill: bool = False):
        try:
            if use_dill:
                with open(path, "rb") as f:
                    model = dill.load(f)
            else:
                model = joblib.load(path)
            self._loaded[name] = True
            log.info("Loaded model: %s", path.name)
            return model
        except Exception as exc:
            log.warning("Could not load %s: %s", path.name, exc)
            self._loaded[name] = False
            return None

    def load_all(self) -> None:
        # lifetimes models saved with dill (lambda serialization)
        self._bgf = self._try_load("bg_nbd", MODELS_DIR / "bg_nbd_model.pkl", use_dill=True)
        self._ggf = self._try_load("gamma_gamma", MODELS_DIR / "gg_model.pkl", use_dill=True)
        # sklearn/xgboost models use standard joblib
        self._xgb = self._try_load("xgb", MODELS_DIR / "xgb_model.pkl")
        self._xgb_scaler = self._try_load("xgb_scaler", MODELS_DIR / "scaler_xgb.pkl")
        self._kmeans = self._try_load("kmeans", MODELS_DIR / "kmeans_model.pkl")
        self._clv_scaler = self._try_load("clv_scaler", MODELS_DIR / "clv_scaler.pkl")

    @property
    def status(self) -> dict[str, bool]:
        return self._loaded

    @property
    def has_bg_nbd(self) -> bool:
        return bool(self._bgf and self._ggf)

    @property
    def has_xgb(self) -> bool:
        return bool(self._xgb and self._xgb_scaler)

    @property
    def has_kmeans(self) -> bool:
        return bool(self._kmeans and self._clv_scaler)


# Singleton registry
_registry = ModelRegistry()


def load_models() -> None:
    """Call once at API startup."""
    _registry.load_all()


def get_model_status() -> dict[str, bool]:
    return _registry.status


# ---------------------------------------------------------------------------
# Feature computation from raw transactions
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "recency", "frequency", "T", "monetary_value",
    "total_revenue", "n_invoices", "purchase_std",
    "days_active", "avg_days_between_purchases",
]


def _compute_features(transactions: list[dict]) -> dict[str, float]:
    """
    Compute RFM + extended features from a list of transaction dicts.

    Each dict must have: invoice_date (date), quantity (float), unit_price (float).
    """
    rows = []
    for t in transactions:
        inv_date = t["invoice_date"]
        if isinstance(inv_date, str):
            inv_date = datetime.strptime(inv_date, "%Y-%m-%d").date()
        revenue = t["quantity"] * t["unit_price"]
        rows.append({"date": inv_date, "revenue": revenue})

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    snapshot = df["date"].max() + timedelta(days=1)
    first_purchase = df["date"].min()
    last_purchase = df["date"].max()

    n_invoices = len(df)
    total_revenue = df["revenue"].sum()
    monetary_value = df["revenue"].mean()
    purchase_std = df["revenue"].std() if len(df) > 1 else 0.0

    recency = (snapshot - last_purchase).days
    T = (snapshot - first_purchase).days
    frequency = max(n_invoices - 1, 0)
    days_active = (last_purchase - first_purchase).days

    avg_days_between = days_active / frequency if frequency > 0 else T

    return {
        "recency": recency,
        "frequency": frequency,
        "T": T,
        "monetary_value": monetary_value,
        "total_revenue": total_revenue,
        "n_invoices": n_invoices,
        "purchase_std": purchase_std if not np.isnan(purchase_std) else 0.0,
        "days_active": days_active,
        "avg_days_between_purchases": avg_days_between,
    }


# ---------------------------------------------------------------------------
# CLV prediction
# ---------------------------------------------------------------------------

TIER_ORDER = ["Bronze", "Silver", "Gold", "Platinum"]


def _assign_tier_fallback(clv: float) -> str:
    """Fallback tier assignment using hardcoded thresholds when K-Means unavailable."""
    # These are rough percentile thresholds from the UCI dataset
    if clv < 50:
        return "Bronze"
    elif clv < 150:
        return "Silver"
    elif clv < 400:
        return "Gold"
    else:
        return "Platinum"


def predict(customer_id: str, transactions: list[dict]) -> dict[str, Any]:
    """
    Compute CLV prediction for a single customer.

    Parameters
    ----------
    customer_id : str
    transactions : list of dicts with keys: invoice_date, quantity, unit_price

    Returns
    -------
    dict with keys matching ScoreResponse schema
    """
    features = _compute_features(transactions)
    n_txns = features["n_invoices"]
    messages: list[str] = []
    models_used: list[str] = []

    clv_bg_nbd: float = 0.0
    expected_purchases: float = 0.0
    churn_risk: float = 0.5
    clv_xgb: float = 0.0

    # ------------------------------------------------------------------ #
    # BG/NBD + Gamma-Gamma scoring
    # ------------------------------------------------------------------ #
    if _registry.has_bg_nbd and features["frequency"] > 0:
        try:
            bgf = _registry._bgf
            ggf = _registry._ggf

            # lifetimes was trained on pandas Series — wrap scalars in arrays
            # so the model's internal numpy operations behave identically
            freq_arr = np.array([features["frequency"]])
            rec_arr  = np.array([features["recency"]])
            T_arr    = np.array([features["T"]])
            mon_arr  = np.array([features["monetary_value"]])

            expected_purchases = float(np.asarray(
                bgf.conditional_expected_number_of_purchases_up_to_time(
                    t=PREDICTION_DAYS,
                    frequency=freq_arr,
                    recency=rec_arr,
                    T=T_arr,
                )
            ).flat[0])

            prob_alive = float(np.asarray(
                bgf.conditional_probability_alive(
                    frequency=freq_arr,
                    recency=rec_arr,
                    T=T_arr,
                )
            ).flat[0])
            churn_risk = 1.0 - prob_alive

            expected_avg_value = float(np.asarray(
                ggf.conditional_expected_average_profit(
                    frequency=freq_arr,
                    monetary_value=mon_arr,
                )
            ).flat[0])

            clv_bg_nbd = max(0.0, expected_purchases * expected_avg_value)
            models_used.append("bg_nbd_gamma_gamma")
        except Exception as exc:
            log.warning("BG/NBD scoring failed for %s: %s", customer_id, exc)
            messages.append("BG/NBD model encountered an error; using fallback.")

    elif features["frequency"] == 0:
        messages.append(
            "Only 1 transaction available — BG/NBD needs repeat purchases. "
            "Using simple revenue projection."
        )
        # Simple heuristic: assume 2 purchases/year at current AOV
        expected_purchases = 2.0
        clv_bg_nbd = expected_purchases * features["monetary_value"] * (PREDICTION_DAYS / 365)
        churn_risk = 0.7  # high risk for single-purchase customers

    # ------------------------------------------------------------------ #
    # XGBoost scoring
    # ------------------------------------------------------------------ #
    if _registry.has_xgb:
        try:
            feat_vec = np.array([[features[c] for c in FEATURE_COLS]])
            feat_scaled = _registry._xgb_scaler.transform(feat_vec)
            clv_xgb = float(max(0.0, _registry._xgb.predict(feat_scaled)[0]))
            models_used.append("xgboost")
        except Exception as exc:
            log.warning("XGB scoring failed for %s: %s", customer_id, exc)

    # ------------------------------------------------------------------ #
    # Ensemble CLV
    # ------------------------------------------------------------------ #
    if clv_bg_nbd > 0 and clv_xgb > 0:
        clv_final = BG_NBD_WEIGHT * clv_bg_nbd + XGB_WEIGHT * clv_xgb
    elif clv_bg_nbd > 0:
        clv_final = clv_bg_nbd
    elif clv_xgb > 0:
        clv_final = clv_xgb
    else:
        clv_final = features["monetary_value"] * 2  # absolute fallback
        messages.append("No trained model available; using AOV heuristic.")

    # ------------------------------------------------------------------ #
    # CLV tier assignment
    # ------------------------------------------------------------------ #
    tier: str
    if _registry.has_kmeans:
        try:
            clv_arr = np.array([[clv_final]])
            clv_scaled = _registry._clv_scaler.transform(clv_arr)
            cluster = int(_registry._kmeans.predict(clv_scaled)[0])
            centroids = _registry._kmeans.cluster_centers_.flatten()
            rank_order = np.argsort(centroids)
            cluster_to_tier = {int(rank_order[i]): TIER_ORDER[i] for i in range(4)}
            tier = cluster_to_tier.get(cluster, "Silver")
        except Exception as exc:
            log.warning("K-Means tier assignment failed: %s", exc)
            tier = _assign_tier_fallback(clv_final)
    else:
        tier = _assign_tier_fallback(clv_final)

    return {
        "customer_id": customer_id,
        "predicted_clv_6months": round(clv_final, 2),
        "clv_tier": tier,
        "churn_risk_score": round(min(max(churn_risk, 0.0), 1.0), 4),
        "expected_purchases_6m": round(expected_purchases, 2),
        "model_used": " + ".join(models_used) if models_used else "heuristic",
        "message": " | ".join(messages) if messages else None,
    }
