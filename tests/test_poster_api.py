from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1 import posters as posters_api
from app.models import PosterOutput
from app.services.posters.renderer import PosterRenderer
from app.services.posters.service import PosterService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting.service import ReportService
from tests.poster_helpers import FakePlaywright
from tests.prediction_helpers import create_prediction_dataset
from tests.reporting_helpers import AvailableLLM


def test_poster_api_generates_and_returns_png_url(
    client: TestClient, session: Session, monkeypatch, tmp_path
) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    report = ReportService(session, llm_client=AvailableLLM()).generate(prediction.id, "internal")
    renderer = PosterRenderer(output_directory=tmp_path, playwright_factory=FakePlaywright)
    monkeypatch.setattr(
        posters_api,
        "PosterService",
        lambda db_session: PosterService(db_session, renderer=renderer),
    )

    created = client.post("/api/v1/posters/generate", json={"report_id": report.report_id})

    assert created.status_code == 201
    poster_id = created.json()["poster_id"]
    fetched = client.get(f"/api/v1/posters/{poster_id}")
    assert fetched.status_code == 200
    assert fetched.json()["image_url"] == f"/generated/posters/{poster_id}.png"
    assert session.scalar(select(func.count()).select_from(PosterOutput)) == 1
