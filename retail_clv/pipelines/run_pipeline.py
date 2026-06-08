"""
pipelines/run_pipeline.py
--------------------------
Pipeline orchestrator — runs all phases end-to-end.

Usage:
    python pipelines/run_pipeline.py
    python pipelines/run_pipeline.py --skip-download
    python pipelines/run_pipeline.py --start-from features
"""

import argparse
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PHASES = ["ingest", "features", "train_bg_nbd", "train_xgboost", "segment"]


def run_phase(name: str, fn, *args, **kwargs):
    log.info("")
    log.info("=" * 65)
    log.info("  PHASE: %s", name.upper())
    log.info("=" * 65)
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.time() - t0
        log.info("✓ Phase '%s' completed in %.1fs", name, elapsed)
        return result
    except Exception as exc:
        log.error("✗ Phase '%s' FAILED: %s", name, exc, exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Run the end-to-end CLV prediction pipeline."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip data download if raw file already exists.",
    )
    parser.add_argument(
        "--start-from",
        choices=PHASES,
        default="ingest",
        help="Resume the pipeline from a specific phase.",
    )
    args = parser.parse_args()

    start_idx = PHASES.index(args.start_from)
    active_phases = PHASES[start_idx:]

    log.info("CLV Prediction Engine — Pipeline Orchestrator")
    log.info("Active phases: %s", " → ".join(active_phases))
    pipeline_start = time.time()

    # ------------------------------------------------------------------
    # Phase 1: Data ingestion
    # ------------------------------------------------------------------
    if "ingest" in active_phases:
        from pipelines.ingest import main as ingest_main
        run_phase("ingest", ingest_main, skip_download=args.skip_download)

    # ------------------------------------------------------------------
    # Phase 2: Feature engineering
    # ------------------------------------------------------------------
    if "features" in active_phases:
        from pipelines.features import main as features_main
        run_phase("features", features_main)

    # ------------------------------------------------------------------
    # Phase 3: BG/NBD + Gamma-Gamma
    # ------------------------------------------------------------------
    if "train_bg_nbd" in active_phases:
        from pipelines.train_bg_nbd import main as bgnbd_main
        run_phase("train_bg_nbd", bgnbd_main)

    # ------------------------------------------------------------------
    # Phase 4: XGBoost + MLflow
    # ------------------------------------------------------------------
    if "train_xgboost" in active_phases:
        from pipelines.train_xgboost import main as xgb_main
        run_phase("train_xgboost", xgb_main)

    # ------------------------------------------------------------------
    # Phase 5: Segmentation
    # ------------------------------------------------------------------
    if "segment" in active_phases:
        from pipelines.segment import main as segment_main
        run_phase("segment", segment_main)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_elapsed = time.time() - pipeline_start
    log.info("")
    log.info("=" * 65)
    log.info("  PIPELINE COMPLETE in %.1fs", total_elapsed)
    log.info("  Output CSV : outputs/clv_scores.csv")
    log.info("  Reports    : outputs/reports/")
    log.info("  Models     : models/")
    log.info("  MLflow UI  : mlflow ui  (then open http://localhost:5000)")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
