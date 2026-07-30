from dataclasses import dataclass
from typing import Any, Literal

from app.services.normalization.match import NormalizedMatch

CompletenessLevel = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class MatchCompleteness:
    level: CompletenessLevel
    match_time_present: bool
    teams_present: bool
    status_present: bool
    injuries_missing: bool


def assess_match_completeness(
    match: NormalizedMatch,
    *,
    injuries: list[dict[str, Any]] | None = None,
) -> MatchCompleteness:
    match_time_present = match.kickoff_at is not None
    teams_present = bool(match.home_team.canonical_name and match.away_team.canonical_name)
    status_present = match.status is not None
    injuries_missing = injuries is None
    essential_complete = match_time_present and teams_present and status_present
    if not essential_complete:
        level: CompletenessLevel = "low"
    elif injuries_missing:
        level = "medium"
    else:
        level = "high"
    return MatchCompleteness(
        level=level,
        match_time_present=match_time_present,
        teams_present=teams_present,
        status_present=status_present,
        injuries_missing=injuries_missing,
    )
