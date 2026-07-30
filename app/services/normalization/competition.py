from dataclasses import dataclass
from typing import Any

from app.services.normalization.names import normalized_key

COMPETITION_ALIASES = {
    "super league china": "CSL",
    "chinese super league": "CSL",
    "major league soccer usa": "MLS",
    "major league soccer united states": "MLS",
    "liga mx mexico": "LIGA_MX",
    "uefa champions league world": "UCL_QUALIFIER",
    "campeonato brasileiro serie a brazil": "BRA_SERIE_A",
    "serie a brazil": "BRA_SERIE_A",
}


@dataclass(frozen=True)
class NormalizedCompetition:
    code: str | None
    external_id: int | None
    provider_name: str | None
    country_name: str | None
    certainty: str = "reported"


def normalize_competition(payload: dict[str, Any]) -> NormalizedCompetition:
    league = payload.get("league", payload)
    country = payload.get("country") if isinstance(payload.get("country"), dict) else {}
    name = league.get("name") if isinstance(league, dict) else None
    country_name = country.get("name") if isinstance(country.get("name"), str) else None
    alias_key = normalized_key(f"{name or ''} {country_name or ''}")
    return NormalizedCompetition(
        code=COMPETITION_ALIASES.get(alias_key),
        external_id=league.get("id") if isinstance(league, dict) and isinstance(league.get("id"), int) else None,
        provider_name=name if isinstance(name, str) else None,
        country_name=country_name,
    )
