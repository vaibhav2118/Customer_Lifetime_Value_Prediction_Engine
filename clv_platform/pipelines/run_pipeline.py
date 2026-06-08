import argparse
import logging
import sys
import time
from clv_platform.pipelines import ingest, features, train_bg_nbd, train_xgboost, segment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

def run_all(limit_rows: int = None):
    t0 = time.time()
    log.info("Starting SaaS CLV Platform End-to-End Pipeline Upgrade...")

    try:
        # Phase 1: Ingestion
        log.info("=== Phase 1: Live Ingestion ===")
        ingest.run_ingestion(limit_rows=limit_rows)

        # Phase 2: Feature Engineering
        log.info("=== Phase 2: Feature Extraction ===")
        features.main()

        # Phase 3: BG/NBD Training
        log.info("=== Phase 3: BG/NBD Probabilistic CLV Training ===")
        train_bg_nbd.main()

        # Phase 4: XGBoost Regression Training
        log.info("=== Phase 4: XGBoost CLV Regression ===")
        train_xgboost.main()

        # Phase 5: Ensembling and Segmentation Tiers
        log.info("=== Phase 5: Ensembling, Segmenting & DB Prediction Logging ===")
        segment.run_segmentation_and_predictions()

        elapsed = time.time() - t0
        log.info("SaaS CLV Platform Pipeline ran successfully in %.2f seconds.", elapsed)
        
    except Exception as e:
        log.exception("Pipeline failed with unexpected error: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-rows", type=int, default=None, help="Limit rows to read for fast testing")
    args = parser.parse_args()
    
    run_all(limit_rows=args.limit_rows)
