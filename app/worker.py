from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()
celery_app = Celery("sakura_football_model", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_ignore_result = True
celery_app.conf.task_track_started = True
celery_app.conf.timezone = "Asia/Shanghai"
celery_app.conf.beat_schedule = {
    "daily-match-scan": {"task": "scheduler.daily_match_scan", "schedule": crontab(hour=8, minute=0)},
    "daily-analysis-generation": {
        "task": "scheduler.daily_analysis_generation",
        "schedule": crontab(hour=8, minute=10),
    },
    "daily-cleanup": {"task": "scheduler.daily_cleanup", "schedule": crontab(hour=3, minute=30)},
    "daily-fixture-sync": {"task": "scheduler.daily_fixture_sync", "schedule": crontab(hour=6, minute=0)},
    "daily-context-sync": {"task": "scheduler.daily_context_sync", "schedule": crontab(hour=6, minute=30)},
    "pre-match-refresh": {"task": "scheduler.pre_match_refresh", "schedule": crontab(minute="*/30")},
    "post-match-result-sync": {"task": "scheduler.post_match_result_sync", "schedule": crontab(hour="*/2")},
}

# Import task modules when the worker starts so task names are registered.
import app.tasks.analysis  # noqa: E402, F401
import app.tasks.scheduler  # noqa: E402, F401
