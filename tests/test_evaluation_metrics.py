import math

import pytest

from app.services.evaluation.metrics import probability_metrics, result_direction


def test_probability_metrics_use_three_way_probabilities() -> None:
    output = {
        "home_win_probability": 0.6,
        "draw_probability": 0.25,
        "away_win_probability": 0.15,
    }

    metrics = probability_metrics(output, "home_win_tendency")

    assert metrics is not None
    assert metrics.log_loss == pytest.approx(-math.log(0.6))
    assert metrics.brier_score == pytest.approx((0.16 + 0.0625 + 0.0225) / 3)
    assert result_direction(2, 1) == "home_win_tendency"
    assert result_direction(0, 2) == "away_win_tendency"
    assert result_direction(1, 1) == "draw_tendency"


def test_probability_metrics_require_complete_probability_output() -> None:
    assert probability_metrics({"home_win_probability": 0.5}, "home_win_tendency") is None
