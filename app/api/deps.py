from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.analysis_jobs import PipelineDispatcher
from app.services.health import HealthService
from app.tasks.analysis import enqueue_analysis_pipeline


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_health_service() -> HealthService:
    return HealthService()


def get_analysis_job_dispatcher() -> PipelineDispatcher:
    return enqueue_analysis_pipeline
