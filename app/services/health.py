from sqlalchemy import text

from app.core.database import engine
from app.core.redis_client import get_redis_client
from app.schemas.health import DependencyStatus, HealthResponse


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
