from app.services.prediction.features.match_features import MatchFeatures
from app.services.prediction.models.poisson import PoissonModel
from app.services.prediction.models.types import ModelOutput, ScoreProbability


class DixonColesModel:
    name = "dixon_coles"
    version = "dixon_coles_v1"

    def __init__(self, rho: float = -0.08) -> None:
        self._rho = rho
        self._poisson = PoissonModel()

    def predict(self, features: MatchFeatures) -> ModelOutput:
        poisson = self._poisson.predict(features)
        if poisson.model_status == "not_available":
            return ModelOutput(
                model_name=self.name,
                model_version=self.version,
                model_status="not_available",
                reason=poisson.reason,
                home_win_probability=None,
                draw_probability=None,
                away_win_probability=None,
                score_probabilities=[],
                expected_home_goals=None,
                expected_away_goals=None,
            )
        assert poisson.expected_home_goals is not None and poisson.expected_away_goals is not None
        adjusted = [
            ScoreProbability(
                item.home_goals,
                item.away_goals,
                item.probability * self._tau(
                    item.home_goals,
                    item.away_goals,
                    poisson.expected_home_goals,
                    poisson.expected_away_goals,
                ),
            )
            for item in poisson.score_probabilities
        ]
        total = sum(item.probability for item in adjusted)
        distribution = [
            ScoreProbability(item.home_goals, item.away_goals, item.probability / total) for item in adjusted
        ]
        home_win = sum(item.probability for item in distribution if item.home_goals > item.away_goals)
        draw = sum(item.probability for item in distribution if item.home_goals == item.away_goals)
        return ModelOutput(
            model_name=self.name,
            model_version=self.version,
            model_status="available",
            reason=None,
            home_win_probability=home_win,
            draw_probability=draw,
            away_win_probability=1 - home_win - draw,
            score_probabilities=distribution,
            expected_home_goals=poisson.expected_home_goals,
            expected_away_goals=poisson.expected_away_goals,
        )

    def _tau(self, home: int, away: int, expected_home: float, expected_away: float) -> float:
        if home == 0 and away == 0:
            return max(0.01, 1 - expected_home * expected_away * self._rho)
        if home == 0 and away == 1:
            return max(0.01, 1 + expected_home * self._rho)
        if home == 1 and away == 0:
            return max(0.01, 1 + expected_away * self._rho)
        if home == 1 and away == 1:
            return max(0.01, 1 - self._rho)
        return 1.0
