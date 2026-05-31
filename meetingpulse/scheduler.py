import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import ConflictingIdError

from tools.overdue import check_and_alert_overdue

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
JOBS_DB_PATH = BASE_DIR / "scheduler_jobs.db"

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("Scheduler already running — skipping re-initialisation.")
        return

    jobstores = {
        "default": SQLAlchemyJobStore(
            url=f"sqlite:///{JOBS_DB_PATH}"
        )
    }

    job_defaults = {
        "misfire_grace_time": 3600,
        "coalesce": True,
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        job_defaults=job_defaults,
        timezone="Asia/Kolkata",
    )

    try:
        _scheduler.add_job(
            func=check_and_alert_overdue,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=9,
                minute=0,
            ),
            id="daily_overdue_check",
            name="Daily overdue action item digest",
            replace_existing=True,
        )
        logger.info(
            "Scheduled job 'daily_overdue_check' — weekdays at 09:00 Asia/Kolkata."
        )
    except ConflictingIdError:
        logger.warning("Job 'daily_overdue_check' already registered — skipping.")

    _scheduler.start()
    logger.info("APScheduler started. Background thread is running.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("APScheduler shut down gracefully.")
