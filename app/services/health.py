from sqlalchemy import text

from app.core.database import engine
from app.core.redis_client import get_redis_client
from app.schemas.health import DependencyStatus, HealthResponse, ServiceHealthResponse


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
        service_status = "ok" if database.status == "ok" and redis_status.status == "ok" else "degraded"
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
