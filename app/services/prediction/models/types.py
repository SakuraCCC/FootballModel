from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ScoreProbability:
    home_goals: int
    away_goals: int
    probability: float

    @property
    def score(self) -> str:
        return f"{self.home_goals}-{self.away_goals}"


@dataclass(frozen=True)
class ModelOutput:
    model_name: str
    model_version: str
    model_status: Literal["available", "not_available"]
    reason: str | None
    home_win_probability: float | None
    draw_probability: float | None
    away_win_probability: float | None
    score_probabilities: list[ScoreProbability]
    expected_home_goals: float | None
    expected_away_goals: float | None

    def top_scores(self, limit: int = 10) -> list[ScoreProbability]:
        return sorted(self.score_probabilities, key=lambda item: item.probability, reverse=True)[:limit]


@dataclass(frozen=True)
class EloOutput:
    model_name: str
    model_version: str
    model_status: Literal["available", "not_available"]
    reason: str | None
    strength_difference: float | None
    home_advantage: float | None
    win_probability_adjustment: float | None
    home_win_probability: float | None
    draw_probability: float | None
    away_win_probability: float | None


def unavailable_model_output(model_name: str, model_version: str, reason: str) -> ModelOutput:
    return ModelOutput(
        model_name=model_name,
        model_version=model_version,
        model_status="not_available",
        reason=reason,
        home_win_probability=None,
        draw_probability=None,
        away_win_probability=None,
        score_probabilities=[],
        expected_home_goals=None,
        expected_away_goals=None,
    )
