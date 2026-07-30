from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DataSource, Match, RawDataSnapshot
from app.services.ingestion.api_football import ApiFootballProvider


class ProviderHealthService:
    """Health information is explicit about unconfigured providers and never leaks keys."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def statuses(self) -> list[dict]:
        sources = list(self._session.scalars(select(DataSource).order_by(DataSource.name)))
        if not sources:
            sources = [None]
        return [self._status_for(source) for source in sources]

    def _status_for(self, source: DataSource | None) -> dict:
        name = source.name if source else "API-Football"
        last_sync = self._session.scalar(
            select(func.max(RawDataSnapshot.retrieved_at)).where(
                RawDataSnapshot.data_source_id == source.id
                if source
                else RawDataSnapshot.provider == name
            )
        )
        quality = self._match_quality(source.id if source else None)
        settings = get_settings()
        if name != "API-Football":
            return {
                "provider": name,
                "status": "unknown",
                "response_time_ms": None,
                "last_sync": last_sync,
                "data_quality": quality,
            }
        if settings.api_football_key is None:
            return {
                "provider": name,
                "status": "unavailable",
                "response_time_ms": None,
                "last_sync": last_sync,
                "data_quality": quality,
            }
        started = perf_counter()
        try:
            ApiFootballProvider().get_competitions()
            return {
                "provider": name,
                "status": "healthy",
                "response_time_ms": round((perf_counter() - started) * 1000, 2),
                "last_sync": last_sync,
                "data_quality": quality,
            }
        except Exception:
            return {
                "provider": name,
                "status": "error",
                "response_time_ms": round((perf_counter() - started) * 1000, 2),
                "last_sync": last_sync,
                "data_quality": quality,
            }

    def _match_quality(self, source_id: str | None) -> str:
        statement = select(Match).order_by(Match.updated_at.desc()).limit(20)
        if source_id:
            statement = statement.where(Match.source_id == source_id)
        matches = list(self._session.scalars(statement))
        if not matches:
            return "low"
        complete = sum(
            bool(item.kickoff_at and item.home_team_id and item.away_team_id) for item in matches
        )
        ratio = complete / len(matches)
        return "high" if ratio >= 0.9 else "medium" if ratio >= 0.5 else "low"
