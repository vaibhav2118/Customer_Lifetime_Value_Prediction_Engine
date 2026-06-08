"""
pipelines/segment.py
--------------------
Phase 5: Customer segmentation via K-Means on CLV scores.

Steps:
  1. Merge BG/NBD and XGBoost CLV scores.
  2. Compute an ensemble CLV = weighted average of both models.
  3. Run K-Means (k=4) on the ensemble CLV.
  4. Map clusters to Bronze / Silver / Gold / Platinum tiers by centroid rank.
  5. Output final CSV: customer_id, predicted_clv_6months, clv_tier, churn_risk_score.

Outputs:
  - models/kmeans_model.pkl
  - models/clv_scaler.pkl
  - outputs/clv_scores.csv

Usage:
    python pipelines/segment.py
"""

import logging
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

BG_NBD_SCORES_PATH = PROCESSED_DIR / "bg_nbd_scores.parquet"
XGB_SCORES_PATH = PROCESSED_DIR / "xgb_scores.parquet"
CLV_SCORES_CSV = OUTPUTS_DIR / "clv_scores.csv"
KMEANS_MODEL_PATH = MODELS_DIR / "kmeans_model.pkl"
CLV_SCALER_PATH = MODELS_DIR / "clv_scaler.pkl"

TIER_MAP = {0: "Bronze", 1: "Silver", 2: "Gold", 3: "Platinum"}
BG_NBD_WEIGHT = 0.6   # BG/NBD carries more weight (domain-driven)
XGB_WEIGHT = 0.4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Merge scores
# ---------------------------------------------------------------------------

def merge_scores() -> pd.DataFrame:
    """Load and merge BG/NBD + XGBoost scores."""
    bg_scores = pd.read_parquet(BG_NBD_SCORES_PATH)
    xgb_scores = pd.read_parquet(XGB_SCORES_PATH)

    merged = bg_scores.merge(xgb_scores, on="CustomerID", how="outer")
    log.info("Merged scores: %d customers", len(merged))

    # Normalise each model's CLV to [0, 1] before weighting
    for col in ["clv_bg_nbd", "clv_xgb"]:
        if col not in merged.columns:
            merged[col] = 0.0
        col_max = merged[col].max()
        if col_max > 0:
            merged[f"{col}_norm"] = merged[col] / col_max
        else:
            merged[f"{col}_norm"] = 0.0

    # Ensemble CLV (weighted average of normalised, re-scaled to £)
    merged["ensemble_clv_norm"] = (
        BG_NBD_WEIGHT * merged["clv_bg_nbd_norm"].fillna(0)
        + XGB_WEIGHT * merged["clv_xgb_norm"].fillna(0)
    )
    # Scale back to original £ space using BG/NBD range
    bgnbd_max = merged["clv_bg_nbd"].max() if "clv_bg_nbd" in merged.columns else 1.0
    merged["predicted_clv_6months"] = (merged["ensemble_clv_norm"] * bgnbd_max).clip(lower=0)

    # Use churn risk from BG/NBD (prob_alive based)
    if "churn_risk_score" not in merged.columns:
        merged["churn_risk_score"] = 0.5
    merged["churn_risk_score"] = merged["churn_risk_score"].fillna(0.5).clip(0, 1)

    return merged


# ---------------------------------------------------------------------------
# K-Means segmentation
# ---------------------------------------------------------------------------

def segment(merged: pd.DataFrame) -> pd.DataFrame:
    """Apply K-Means (k=4) and assign CLV tiers."""

    X = merged[["predicted_clv_6months"]].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    log.info("Running K-Means with k=4…")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=20, max_iter=500)
    kmeans.fit(X_scaled)

    merged["cluster"] = kmeans.labels_

    # Map cluster → tier by centroid rank (ascending CLV → Bronze first)
    centroids = kmeans.cluster_centers_.flatten()
    rank_order = np.argsort(centroids)           # ascending: lowest CLV cluster first
    cluster_to_tier = {int(rank_order[i]): TIER_MAP[i] for i in range(4)}

    merged["clv_tier"] = merged["cluster"].map(cluster_to_tier)

    log.info("Tier distribution:")
    for tier in ["Bronze", "Silver", "Gold", "Platinum"]:
        count = (merged["clv_tier"] == tier).sum()
        pct = 100 * count / len(merged)
        avg_clv = merged.loc[merged["clv_tier"] == tier, "predicted_clv_6months"].mean()
        log.info("  %-10s %5d customers (%5.1f%%)  avg CLV=£%.2f", tier, count, pct, avg_clv)

    # Persist models
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(kmeans, KMEANS_MODEL_PATH)
    joblib.dump(scaler, CLV_SCALER_PATH)
    log.info("Saved K-Means model: %s", KMEANS_MODEL_PATH)

    return merged


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def generate_output(merged: pd.DataFrame) -> pd.DataFrame:
    """Produce the final deliverable CSV."""
    output = merged[[
        "CustomerID",
        "predicted_clv_6months",
        "clv_tier",
        "churn_risk_score",
        "expected_purchases_6m",
        "prob_alive",
        "clv_bg_nbd",
        "clv_xgb",
    ]].copy()

    output = output.rename(columns={"CustomerID": "customer_id"})
    output = output.sort_values("predicted_clv_6months", ascending=False)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(CLV_SCORES_CSV, index=False, float_format="%.4f")
    log.info("Saved CLV scores CSV: %s (%d customers)", CLV_SCORES_CSV, len(output))

    # Quick sanity check
    assert output["clv_tier"].nunique() == 4, "Expected exactly 4 CLV tiers!"
    assert output["predicted_clv_6months"].isna().sum() == 0, "Null CLV scores found!"

    return output


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def generate_segment_report(output: pd.DataFrame) -> None:
    """Save a tier distribution and CLV density chart."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        tier_order = ["Bronze", "Silver", "Gold", "Platinum"]
        palette = {"Bronze": "#cd7f32", "Silver": "#aaa9ad", "Gold": "#ffd700", "Platinum": "#e5e4e2"}

        # --- Tier count bar chart ---
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("Customer CLV Segmentation", fontsize=14, fontweight="bold")

        tier_counts = output["clv_tier"].value_counts().reindex(tier_order)
        colors = [palette[t] for t in tier_order]
        axes[0].bar(tier_order, tier_counts.values, color=colors, edgecolor="black", linewidth=0.7)
        axes[0].set_title("Customer Count by Tier")
        axes[0].set_xlabel("CLV Tier")
        axes[0].set_ylabel("Number of Customers")
        for i, v in enumerate(tier_counts.values):
            axes[0].text(i, v + 5, str(v), ha="center", fontsize=10)

        # --- CLV distribution by tier (box plot) ---
        order_mask = output["clv_tier"].isin(tier_order)
        sns.boxplot(
            data=output[order_mask],
            x="clv_tier",
            y="predicted_clv_6months",
            order=tier_order,
            palette=palette,
            ax=axes[1],
            flierprops={"marker": "o", "markersize": 2},
        )
        axes[1].set_title("CLV Distribution by Tier")
        axes[1].set_xlabel("CLV Tier")
        axes[1].set_ylabel("Predicted CLV — 6 months (£)")

        plt.tight_layout()
        chart_path = PROJECT_ROOT / "outputs" / "reports" / "clv_segment_report.png"
        chart_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info("Segment report chart saved: %s", chart_path)

        # --- Churn risk vs CLV scatter ---
        fig2, ax2 = plt.subplots(figsize=(9, 6))
        for tier in tier_order:
            mask = output["clv_tier"] == tier
            ax2.scatter(
                output.loc[mask, "predicted_clv_6months"],
                output.loc[mask, "churn_risk_score"],
                label=tier,
                alpha=0.5,
                s=15,
                color=palette[tier],
            )
        ax2.set_xlabel("Predicted CLV — 6 months (£)")
        ax2.set_ylabel("Churn Risk Score")
        ax2.set_title("CLV vs Churn Risk by Tier")
        ax2.legend(title="Tier")
        fig2.savefig(
            PROJECT_ROOT / "outputs" / "reports" / "clv_vs_churn_risk.png",
            dpi=150, bbox_inches="tight",
        )
        plt.close(fig2)
        log.info("CLV vs Churn Risk chart saved.")

    except Exception as exc:
        log.warning("Could not generate segment report: %s", exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> pd.DataFrame:
    for path in [BG_NBD_SCORES_PATH, XGB_SCORES_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required scores file not found: {path}\n"
                "Run train_bg_nbd.py and train_xgboost.py first."
            )

    merged = merge_scores()
    merged = segment(merged)
    output = generate_output(merged)
    generate_segment_report(output)
    return output


if __name__ == "__main__":
    main()
