from dataclasses import dataclass
from typing import Any

from app.services.normalization.names import canonical_team_name, normalized_key


@dataclass(frozen=True)
class NormalizedTeam:
    external_id: str | None
    canonical_name: str | None
    normalized_name: str | None
    country_code: str | None
    certainty: str = "reported"


def normalize_team(payload: dict[str, Any]) -> NormalizedTeam:
    team = payload.get("team", payload)
    raw_name = team.get("name") if isinstance(team, dict) else None
    canonical_name = canonical_team_name(raw_name) if isinstance(raw_name, str) and raw_name.strip() else None
    country = payload.get("country") if isinstance(payload.get("country"), dict) else {}
    return NormalizedTeam(
        external_id=str(team["id"]) if isinstance(team, dict) and team.get("id") is not None else None,
        canonical_name=canonical_name,
        normalized_name=normalized_key(canonical_name) if canonical_name else None,
        country_code=country.get("code") if isinstance(country.get("code"), str) else None,
    )
