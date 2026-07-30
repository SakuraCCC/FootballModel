from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("sakura_football_model", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_ignore_result = True
celery_app.conf.task_track_started = True

# Import task modules when the worker starts so task names are registered.
import app.tasks.analysis  # noqa: E402, F401
