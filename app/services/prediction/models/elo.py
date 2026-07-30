from app.services.prediction.features.match_features import MatchFeatures
from app.services.prediction.models.types import EloOutput


class EloModel:
    name = "elo"
    version = "elo_v1"

    def __init__(self, k_factor: float = 20.0, home_advantage: float = 65.0) -> None:
        self._k_factor = k_factor
        self._home_advantage = home_advantage

    def predict(self, features: MatchFeatures) -> EloOutput:
        home_id = features.home_team.team_id
        away_id = features.away_team.team_id
        if home_id is None or away_id is None or not features.historical_results:
            return EloOutput(
                self.name,
                self.version,
                "not_available",
                "Historical results are required.",
                None,
                None,
                None,
                None,
                None,
                None,
            )
        ratings: dict[str, float] = {}
        appearances: dict[str, int] = {}
        for result in features.historical_results:
            if result.home_team_id is None or result.away_team_id is None:
                continue
            home_rating = ratings.get(result.home_team_id, 1500.0)
            away_rating = ratings.get(result.away_team_id, 1500.0)
            expected_home = self._expected(home_rating + self._home_advantage, away_rating)
            actual_home = 1.0 if result.home_score > result.away_score else 0.5 if result.home_score == result.away_score else 0.0
            delta = self._k_factor * (actual_home - expected_home)
            ratings[result.home_team_id] = home_rating + delta
            ratings[result.away_team_id] = away_rating - delta
            appearances[result.home_team_id] = appearances.get(result.home_team_id, 0) + 1
            appearances[result.away_team_id] = appearances.get(result.away_team_id, 0) + 1
        if appearances.get(home_id, 0) < 3 or appearances.get(away_id, 0) < 3:
            return EloOutput(
                self.name,
                self.version,
                "not_available",
                "At least three historical matches per team are required.",
                None,
                None,
                None,
                None,
                None,
                None,
            )
        difference = ratings.get(home_id, 1500.0) - ratings.get(away_id, 1500.0)
        expected_home = self._expected(ratings.get(home_id, 1500.0) + self._home_advantage, ratings.get(away_id, 1500.0))
        draw_probability = 0.25
        home_probability = expected_home * (1 - draw_probability)
        away_probability = (1 - expected_home) * (1 - draw_probability)
        return EloOutput(
            self.name,
            self.version,
            "available",
            None,
            difference,
            self._home_advantage,
            (expected_home - 0.5) * 0.2,
            home_probability,
            draw_probability,
            away_probability,
        )

    @staticmethod
    def _expected(home_rating: float, away_rating: float) -> float:
        return 1 / (1 + 10 ** ((away_rating - home_rating) / 400))
