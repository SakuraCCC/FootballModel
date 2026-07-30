from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.services.prediction.features.team_features import TeamFeatures


@dataclass(frozen=True)
class HistoricalResult:
    match_id: str
    kickoff_at: datetime
    home_team_id: str | None
    away_team_id: str | None
    home_score: int
    away_score: int


@dataclass(frozen=True)
class MatchFeatures:
    match_id: str
    competition_id: str
    home_team: TeamFeatures
    away_team: TeamFeatures
    league_average_goals: float | None
    data_completeness: Literal["high", "medium", "low"]
    missing_fields: list[str]
    input_snapshot_id: str | None
    historical_results: list[HistoricalResult]
