from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import AutomationRun, Competition, Match, Team


@dataclass(frozen=True)
class UpcomingMatch:
    match_id: str
    competition_code: str
    competition_name: str
    home_team: str | None
    away_team: str | None
    kickoff_at: datetime


class MatchScanner:
    """Find persisted fixtures eligible for the 24–72 hour automation window."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def scan(self, now: datetime | None = None) -> list[UpcomingMatch]:
        current = now or datetime.now(UTC)
        start = current + timedelta(hours=24)
        end = current + timedelta(hours=72)
        home = Team.__table__.alias("home")
        away = Team.__table__.alias("away")
        statement = (
            select(
                Match.id,
                Competition.code,
                Competition.name,
                home.c.canonical_name,
                away.c.canonical_name,
                Match.kickoff_at,
            )
            .join(Competition, Competition.id == Match.competition_id)
            .outerjoin(home, home.c.id == Match.home_team_id)
            .outerjoin(away, away.c.id == Match.away_team_id)
            .outerjoin(AutomationRun, AutomationRun.match_id == Match.id)
            .where(
                Match.kickoff_at >= start,
                Match.kickoff_at <= end,
                Match.status.in_(("scheduled", "NS", "TBD")),
                or_(AutomationRun.id.is_(None), AutomationRun.status.in_(("pending", "failed"))),
            )
            .order_by(Match.kickoff_at.asc())
        )
        return [
            UpcomingMatch(
                match_id=match_id,
                competition_code=code,
                competition_name=name,
                home_team=home_name,
                away_team=away_name,
                kickoff_at=kickoff_at,
            )
            for match_id, code, name, home_name, away_name, kickoff_at in self._session.execute(statement)
            if kickoff_at is not None
        ]
