from app.services.prediction.models.types import ScoreProbability
from app.services.prediction.simulation import ScoreSimulator


def test_score_simulator_runs_probability_weighted_ten_thousand_draws() -> None:
    result = ScoreSimulator().simulate(
        [ScoreProbability(1, 0, 0.6), ScoreProbability(1, 1, 0.3), ScoreProbability(0, 0, 0.1)],
        seed="match-1",
    )

    assert result.simulations == 10_000
    assert sum(item.occurrences for item in result.scores) == 10_000
    assert result.scores[0].score == "1-0"
    assert result.low_confidence is False
