from datetime import timedelta

from sqlalchemy.orm import Session

from app.services.backtest import BacktestPipeline
from app.services.results import ResultService
from tests.prediction_helpers import create_prediction_dataset


def test_backtest_replays_completed_matches_without_future_data(session: Session) -> None:
    target = create_prediction_dataset(session)
    ResultService(session).record(
        match_id=target.id,
        home_score=2,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
        result_source_id=None,
        notes="test final result",
    )

    result = BacktestPipeline(session).run(competition_code="CSL")

    assert result.processed == 7
    assert result.evaluated == 1
    assert result.skipped_not_available == 6
    assert len(result.prediction_ids) == 7
