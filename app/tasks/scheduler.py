import logging

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.operations import DailyOperationReportService
from app.services.scheduler import AutomationPipeline, MatchScanner, record_heartbeat
from app.services.scheduler.cleanup import TemporaryFileCleaner
from app.services.scheduler.ingestion_tasks import (
    refresh_pre_match_context,
    sync_context,
    sync_daily_results,
    sync_daily_standings,
    sync_future_fixtures,
)
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="scheduler.daily_match_scan")
def daily_match_scan() -> list[str]:
    session = SessionLocal()
    try:
        record_heartbeat(session, "daily_match_scan")
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
        record_heartbeat(session, "automate_match", self.request.id)
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
        record_heartbeat(session, "daily_analysis_generation")
        matches = MatchScanner(session).scan()
        task_ids = [automate_match.delay(item.match_id).id for item in matches]
        logger.info("daily_analysis_generation_enqueued match_count=%s", len(task_ids))
        return task_ids
    finally:
        session.close()


@celery_app.task(name="scheduler.daily_cleanup")
def daily_cleanup() -> int:
    session = SessionLocal()
    try:
        try:
            record_heartbeat(session, "daily_cleanup")
        except Exception:
            # Cleanup remains safe and useful even while the database is temporarily unavailable.
            logger.warning("daily_cleanup_heartbeat_unavailable")
        removed = TemporaryFileCleaner(get_settings().temporary_file_dir).remove_expired()
        logger.info("daily_cleanup_completed removed=%s", removed)
        return removed
    finally:
        session.close()


@celery_app.task(name="scheduler.daily_operation_report")
def daily_operation_report() -> str:
    session = SessionLocal()
    try:
        record_heartbeat(session, "daily_operation_report")
        report = DailyOperationReportService(session).get_or_build()
        logger.info("daily_operation_report_completed report_id=%s", report.id)
        return report.id
    finally:
        session.close()


@celery_app.task(name="scheduler.daily_fixture_sync")
def daily_fixture_sync() -> dict[str, int]:
    return sync_future_fixtures()


@celery_app.task(name="scheduler.daily_context_sync")
def daily_context_sync() -> dict[str, int]:
    return sync_context()


@celery_app.task(name="scheduler.daily_standings_sync")
def daily_standings_sync() -> dict[str, int]:
    return sync_daily_standings()


@celery_app.task(name="scheduler.daily_result_sync")
def daily_result_sync() -> int:
    return sync_daily_results()


@celery_app.task(name="scheduler.pre_match_refresh")
def pre_match_refresh() -> int:
    return refresh_pre_match_context()


@celery_app.task(name="scheduler.post_match_result_sync")
def post_match_result_sync() -> int:
    return sync_daily_results()
