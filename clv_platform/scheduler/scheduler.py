import logging
import time
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from clv_platform.pipelines import run_pipeline, segment
from clv_platform.api.predictor import load_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

def daily_prediction_refresh():
    log.info("[Scheduler] Starting daily prediction refresh...")
    try:
        segment.run_segmentation_and_predictions()
        log.info("[Scheduler] Daily prediction refresh completed successfully.")
    except Exception as e:
        log.error("[Scheduler] Daily prediction refresh failed: %s", e)

def weekly_model_retraining():
    log.info("[Scheduler] Starting weekly model retraining pipeline...")
    try:
        run_pipeline.run_all()
        # Trigger reload of predictions/models
        load_models()
        log.info("[Scheduler] Weekly model retraining completed and models reloaded.")
    except Exception as e:
        log.error("[Scheduler] Weekly model retraining failed: %s", e)

def start_scheduler():
    scheduler = BlockingScheduler()
    
    # Schedule prediction refresh to run daily at midnight
    scheduler.add_job(
        daily_prediction_refresh,
        'cron',
        hour=0,
        minute=0,
        id='daily_refresh',
        replace_existing=True
    )
    
    # Schedule retraining to run weekly on Sunday at 2 AM
    scheduler.add_job(
        weekly_model_retraining,
        'cron',
        day_of_week='sun',
        hour=2,
        minute=0,
        id='weekly_retrain',
        replace_existing=True
    )
    
    log.info("APScheduler initialized. Daily refresh (00:00) and Weekly retraining (Sun 02:00) are active.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")

if __name__ == "__main__":
    start_scheduler()
