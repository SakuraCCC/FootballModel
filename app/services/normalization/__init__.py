"""Transforms provider payloads into provider-independent records."""

from app.services.normalization.competition import NormalizedCompetition, normalize_competition
from app.services.normalization.match import NormalizedMatch, normalize_match
from app.services.normalization.player import NormalizedPlayer, normalize_player
from app.services.normalization.team import NormalizedTeam, normalize_team

__all__ = [
    "NormalizedCompetition",
    "NormalizedMatch",
    "NormalizedPlayer",
    "NormalizedTeam",
    "normalize_competition",
    "normalize_match",
    "normalize_player",
    "normalize_team",
]
