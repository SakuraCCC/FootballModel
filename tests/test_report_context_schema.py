from sqlalchemy.orm import Session

from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting.builder import ReportContextBuilder
from tests.prediction_helpers import create_prediction_dataset


def test_report_context_preserves_source_and_certainty(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    context = ReportContextBuilder(session).build(prediction.id)

    assert context.match_info["home_team"] == "Home FC"
    assert context.confirmed_facts == []
    assert context.reported_information[0].certainty == "reported"
    assert context.source_snapshots[0].provider == "API-Football"
    assert context.model_prediction["direction"] == prediction.direction
