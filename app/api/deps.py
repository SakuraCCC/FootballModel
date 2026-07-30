from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.health import HealthService


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_health_service() -> HealthService:
    return HealthService()
