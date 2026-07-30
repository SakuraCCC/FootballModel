import math

from app.services.prediction.features.match_features import MatchFeatures
from app.services.prediction.models.types import (
    ModelOutput,
    ScoreProbability,
    unavailable_model_output,
)


class PoissonModel:
    name = "poisson"
    version = "poisson_v1"
    max_goals = 8

    def predict(self, features: MatchFeatures) -> ModelOutput:
        if not self._has_required_data(features):
            return unavailable_model_output(
                self.name,
                self.version,
                "At least three historical results per team and a league goal average are required.",
            )
        league_average = features.league_average_goals
        assert league_average is not None
        home = features.home_team
        away = features.away_team
        assert home.recent_goals_for is not None and home.recent_goals_against is not None
        assert away.recent_goals_for is not None and away.recent_goals_against is not None
        home_attack = home.recent_goals_for / league_average
        home_defense = home.recent_goals_against / league_average
        away_attack = away.recent_goals_for / league_average
        away_defense = away.recent_goals_against / league_average
        expected_home = max(0.05, league_average * home_attack * away_defense * 1.10)
        expected_away = max(0.05, league_average * away_attack * home_defense)
        distribution = self._distribution(expected_home, expected_away)
        home_win, draw, away_win = self._outcomes(distribution)
        return ModelOutput(
            model_name=self.name,
            model_version=self.version,
            model_status="available",
            reason=None,
            home_win_probability=home_win,
            draw_probability=draw,
            away_win_probability=away_win,
            score_probabilities=distribution,
            expected_home_goals=expected_home,
            expected_away_goals=expected_away,
        )

    def _distribution(self, expected_home: float, expected_away: float) -> list[ScoreProbability]:
        raw = [
            ScoreProbability(home, away, self._pmf(home, expected_home) * self._pmf(away, expected_away))
            for home in range(self.max_goals + 1)
            for away in range(self.max_goals + 1)
        ]
        total = sum(item.probability for item in raw)
        return [ScoreProbability(item.home_goals, item.away_goals, item.probability / total) for item in raw]

    @staticmethod
    def _pmf(goals: int, expected_goals: float) -> float:
        return math.exp(-expected_goals) * expected_goals**goals / math.factorial(goals)

    @staticmethod
    def _outcomes(distribution: list[ScoreProbability]) -> tuple[float, float, float]:
        home_win = sum(item.probability for item in distribution if item.home_goals > item.away_goals)
        draw = sum(item.probability for item in distribution if item.home_goals == item.away_goals)
        away_win = 1 - home_win - draw
        return home_win, draw, away_win

    @staticmethod
    def _has_required_data(features: MatchFeatures) -> bool:
        return bool(
            features.league_average_goals
            and features.home_team.historical_match_count >= 3
            and features.away_team.historical_match_count >= 3
            and features.home_team.recent_goals_for is not None
            and features.home_team.recent_goals_against is not None
            and features.away_team.recent_goals_for is not None
            and features.away_team.recent_goals_against is not None
        )
