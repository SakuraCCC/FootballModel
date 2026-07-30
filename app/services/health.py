from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.database import engine
from app.core.redis_client import get_redis_client
from app.schemas.health import (
    DependencyStatus,
    HealthResponse,
    SchedulerHealthResponse,
    ServiceHealthResponse,
)


class HealthService:
    def check_database(self) -> DependencyStatus:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return DependencyStatus(status="ok")
        except Exception:
            return DependencyStatus(status="error")

    def check_redis(self) -> DependencyStatus:
        try:
            get_redis_client().ping()
            return DependencyStatus(status="ok")
        except Exception:
            return DependencyStatus(status="error")

    def check(self) -> HealthResponse:
        database = self.check_database()
        redis_status = self.check_redis()
        service_status = (
            "ok" if database.status == "ok" and redis_status.status == "ok" else "degraded"
        )
        return HealthResponse(status=service_status, database=database, redis=redis_status)

    def database_health(self) -> ServiceHealthResponse:
        return ServiceHealthResponse(status=self.check_database().status)

    def worker_health(self) -> ServiceHealthResponse:
        try:
            from app.worker import celery_app

            replies = celery_app.control.inspect(timeout=1.0).ping() or {}
            return ServiceHealthResponse(status="ok" if replies else "error")
        except Exception:
            return ServiceHealthResponse(status="error")

    def scheduler_health(self) -> SchedulerHealthResponse:
        database = self.check_database()
        redis_status = self.check_redis()
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT last_executed_at FROM scheduler_heartbeats ORDER BY last_executed_at DESC LIMIT 1"
                    )
                ).first()
            last_execution = row[0] if row else None
            now = datetime.now(UTC)
            if last_execution is not None and last_execution.tzinfo is None:
                last_execution = last_execution.replace(tzinfo=UTC)
            beat_ok = last_execution is not None and now - last_execution <= timedelta(hours=36)
        except Exception:
            last_execution = None
            beat_ok = False
        status = (
            "ok" if database.status == "ok" and redis_status.status == "ok" and beat_ok else "error"
        )
        return SchedulerHealthResponse(
            status=status,
            database=database,
            redis=redis_status,
            beat_status="ok" if beat_ok else "error",
            last_task_execution=last_execution.isoformat() if last_execution else None,
        )
