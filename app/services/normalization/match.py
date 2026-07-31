from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.normalization.team import NormalizedTeam, normalize_team


@dataclass(frozen=True)
class NormalizedMatch:
    external_id: str | None
    kickoff_at: datetime | None
    status: str | None
    home_team: NormalizedTeam
    away_team: NormalizedTeam
    round_name: str | None
    certainty: str = "reported"
    home_score: int | None = None
    away_score: int | None = None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_match(payload: dict[str, Any]) -> NormalizedMatch:
    fixture = payload.get("fixture") if isinstance(payload.get("fixture"), dict) else {}
    league = payload.get("league") if isinstance(payload.get("league"), dict) else {}
    teams = payload.get("teams") if isinstance(payload.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}
    goals = payload.get("goals") if isinstance(payload.get("goals"), dict) else {}
    return NormalizedMatch(
        external_id=str(fixture["id"]) if fixture.get("id") is not None else None,
        kickoff_at=_parse_datetime(fixture.get("date")),
        status=status.get("short") if isinstance(status.get("short"), str) else None,
        home_team=normalize_team({"team": home}),
        away_team=normalize_team({"team": away}),
        round_name=league.get("round") if isinstance(league.get("round"), str) else None,
        home_score=goals.get("home") if isinstance(goals.get("home"), int) else None,
        away_score=goals.get("away") if isinstance(goals.get("away"), int) else None,
    )
