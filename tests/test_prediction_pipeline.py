from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ModelRun, PredictionResult
from app.services.prediction.pipeline import PredictionPipeline
from tests.prediction_helpers import create_prediction_dataset


def test_prediction_pipeline_persists_auditable_model_runs_and_result(session: Session) -> None:
    target = create_prediction_dataset(session)

    prediction = PredictionPipeline(session).run(target.id)
    stored = session.get(PredictionResult, prediction.id)
    model_run_count = session.scalar(select(func.count()).select_from(ModelRun).where(ModelRun.match_id == target.id))

    assert stored is not None
    assert stored.status == "available"
    assert stored.direction == "home_win_tendency"
    assert stored.primary_score is not None
    assert stored.review_summary["round_3_fatigue_injuries_data_quality"]["injuries_used"] is False
    assert stored.confidence == "medium"
    assert model_run_count == 4


def test_prediction_api_runs_and_returns_persisted_result(client: TestClient, session: Session) -> None:
    target = create_prediction_dataset(session)

    run_response = client.post("/api/v1/predictions/run", json={"match_id": target.id})

    assert run_response.status_code == 201
    prediction_id = run_response.json()["prediction_id"]
    get_response = client.get(f"/api/v1/predictions/{prediction_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "available"
    assert get_response.json()["model_output"]["model_status"] == "available"
