import logging

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.scheduler import AutomationPipeline, MatchScanner
from app.services.scheduler.cleanup import TemporaryFileCleaner
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="scheduler.daily_match_scan")
def daily_match_scan() -> list[str]:
    session = SessionLocal()
    try:
        matches = MatchScanner(session).scan()
        ids = [item.match_id for item in matches]
        logger.info("daily_match_scan_completed match_count=%s", len(ids))
        return ids
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="scheduler.automate_match",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def automate_match(self, match_id: str) -> str:
    session = SessionLocal()
    try:
        run = AutomationPipeline(session).run(
            match_id,
            task_id=self.request.id,
            retry_count=self.request.retries,
        )
        return run.id
    finally:
        session.close()


@celery_app.task(name="scheduler.daily_analysis_generation")
def daily_analysis_generation() -> list[str]:
    session = SessionLocal()
    try:
        matches = MatchScanner(session).scan()
        task_ids = [automate_match.delay(item.match_id).id for item in matches]
        logger.info("daily_analysis_generation_enqueued match_count=%s", len(task_ids))
        return task_ids
    finally:
        session.close()


@celery_app.task(name="scheduler.daily_cleanup")
def daily_cleanup() -> int:
    removed = TemporaryFileCleaner(get_settings().temporary_file_dir).remove_expired()
    logger.info("daily_cleanup_completed removed=%s", removed)
    return removed
