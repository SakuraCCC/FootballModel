import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ProbabilityMetrics:
    log_loss: float
    brier_score: float


def result_direction(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win_tendency"
    if home_score < away_score:
        return "away_win_tendency"
    return "draw_tendency"


def probability_metrics(output: dict, actual_direction: str) -> ProbabilityMetrics | None:
    probabilities = {
        "home_win_tendency": output.get("home_win_probability"),
        "draw_tendency": output.get("draw_probability"),
        "away_win_tendency": output.get("away_win_probability"),
    }
    if not all(isinstance(value, (float, int)) for value in probabilities.values()):
        return None
    normalized_total = sum(float(value) for value in probabilities.values())
    if normalized_total <= 0:
        return None
    normalized = {key: float(value) / normalized_total for key, value in probabilities.items()}
    actual_probability = max(normalized[actual_direction], 1e-15)
    brier = sum(
        (probability - (1.0 if direction == actual_direction else 0.0)) ** 2
        for direction, probability in normalized.items()
    ) / 3
    return ProbabilityMetrics(log_loss=-math.log(actual_probability), brier_score=brier)


def output_direction(output: dict) -> str | None:
    probabilities = {
        "home_win_tendency": output.get("home_win_probability"),
        "draw_tendency": output.get("draw_probability"),
        "away_win_tendency": output.get("away_win_probability"),
    }
    if not all(isinstance(value, (float, int)) for value in probabilities.values()):
        return None
    return max(probabilities, key=probabilities.get)
