from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ContentPublishRecord, PosterOutput, ReportOutput
from app.services.prediction.pipeline import PredictionPipeline
from tests.prediction_helpers import create_prediction_dataset


def test_dashboard_aggregates_content_assets(client: TestClient, session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    report = ReportOutput(
        prediction_id=prediction.id,
        report_type="xiaohongshu",
        content="content",
        prompt_version="test",
        llm_model="test",
        status="generated",
        warnings=[],
    )
    session.add(report)
    session.flush()
    poster = PosterOutput(
        report_id=report.id,
        prediction_id=prediction.id,
        competition_style="CSL",
        file_path="generated/posters/test.png",
        template_version="test",
    )
    session.add(poster)
    session.flush()
    session.add(
        ContentPublishRecord(
            report_id=report.id,
            poster_id=poster.id,
            platform="manual",
            publish_time=datetime.now(UTC),
        )
    )
    session.commit()

    summary = client.get("/api/v1/dashboard/summary")
    assets = client.get("/api/v1/dashboard/content-assets?competition_code=CSL")
    performance = client.get("/api/v1/dashboard/model-performance")

    assert summary.status_code == 200
    assert summary.json()["total_predictions"] == 1
    assert summary.json()["total_reports"] == 1
    assert summary.json()["total_posters"] == 1
    assert assets.status_code == 200
    assert assets.json() == {
        "report_count": 1,
        "poster_count": 1,
        "published_count": 1,
        "unpublished_count": 0,
    }
    assert performance.status_code == 200
    assert performance.json()["sample_count"] == 0
