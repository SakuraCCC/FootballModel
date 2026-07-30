from dataclasses import dataclass

from app.services.prediction.models.types import (
    EloOutput,
    ModelOutput,
    ScoreProbability,
    unavailable_model_output,
)


@dataclass(frozen=True)
class EnsembleOutput:
    model_output: ModelOutput
    total_goal_range: str | None
    btts: str | None


class EnsembleModel:
    name = "ensemble"
    version = "ensemble_v1"

    def combine(self, poisson: ModelOutput, dixon_coles: ModelOutput, elo: EloOutput) -> EnsembleOutput:
        available = [output for output in (poisson, dixon_coles) if output.model_status == "available"]
        if not available:
            return EnsembleOutput(
                unavailable_model_output(self.name, self.version, "Goal models are not available."), None, None
            )
        home = sum(output.home_win_probability or 0 for output in available) / len(available)
        draw = sum(output.draw_probability or 0 for output in available) / len(available)
        away = sum(output.away_win_probability or 0 for output in available) / len(available)
        if elo.model_status == "available" and elo.win_probability_adjustment is not None:
            home = max(0.0, home + elo.win_probability_adjustment)
            away = max(0.0, away - elo.win_probability_adjustment)
        total = home + draw + away
        distribution = self._combine_distributions(available)
        expected_home = sum(output.expected_home_goals or 0 for output in available) / len(available)
        expected_away = sum(output.expected_away_goals or 0 for output in available) / len(available)
        model_output = ModelOutput(
            model_name=self.name,
            model_version=self.version,
            model_status="available",
            reason=None,
            home_win_probability=home / total,
            draw_probability=draw / total,
            away_win_probability=away / total,
            score_probabilities=distribution,
            expected_home_goals=expected_home,
            expected_away_goals=expected_away,
        )
        total_expected = expected_home + expected_away
        goal_range = f"{max(0, int(total_expected - 0.75))}-{int(total_expected + 1.25)}"
        btts_probability = sum(
            item.probability
            for item in distribution
            if item.home_goals > 0 and item.away_goals > 0
        )
        return EnsembleOutput(
            model_output=model_output,
            total_goal_range=goal_range,
            btts="likely" if btts_probability >= 0.5 else "unlikely",
        )

    @staticmethod
    def _combine_distributions(available: list[ModelOutput]) -> list[ScoreProbability]:
        values: dict[tuple[int, int], float] = {}
        for output in available:
            for score in output.score_probabilities:
                key = (score.home_goals, score.away_goals)
                values[key] = values.get(key, 0.0) + score.probability / len(available)
        return [ScoreProbability(home, away, probability) for (home, away), probability in values.items()]
