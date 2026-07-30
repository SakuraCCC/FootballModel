from sqlalchemy.orm import Session

from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting.builder import ReportContextBuilder
from app.services.reporting.fact_checker import FactChecker
from tests.prediction_helpers import create_prediction_dataset


def test_fact_checker_prevents_reported_information_from_becoming_confirmed(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    context = ReportContextBuilder(session).build(prediction.id)

    result = FactChecker().check(context, "官方确认：比赛信息。模型方向为主队。")

    assert result.status == "warning"
    assert "reported_information_must_not_be_presented_as_confirmed" in result.warnings
