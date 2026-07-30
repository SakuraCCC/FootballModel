from dataclasses import dataclass


@dataclass(frozen=True)
class TeamFeatures:
    team_id: str | None
    recent_form: list[str] | None
    recent_goals_for: float | None
    recent_goals_against: float | None
    home_form: list[str] | None
    away_form: list[str] | None
    league_rank: int | None
    points: int | None
    goal_difference: int | None
    rest_days: int | None
    historical_match_count: int
    recent_goals_trend: float | None = None
    recent_conceded_trend: float | None = None
    recent_shots_trend: float | None = None
    recent_xg_trend: float | None = None
