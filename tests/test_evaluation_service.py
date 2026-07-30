from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ModelPerformance, ModelRun
from app.services.evaluation import EvaluationService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.results import ResultService
from tests.prediction_helpers import create_prediction_dataset


def test_evaluation_persists_metrics_and_model_comparison(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    actual = ResultService(session).record(
        match_id=target.id,
        home_score=2,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
        result_source_id=None,
        notes="test final result",
    )

    evaluation = EvaluationService(session).evaluate(prediction.id, actual.id)
    summary = EvaluationService(session).summary("CSL")

    assert evaluation.prediction_id == prediction.id
    assert evaluation.actual_result_id == actual.id
    assert evaluation.log_loss is not None
    assert evaluation.brier_score is not None
    assert summary["sample_count"] == 1
    assert len(summary["models"]) == 4
    assert session.scalar(select(func.count()).select_from(ModelPerformance)) == 4
    assert session.scalar(
        select(func.count()).select_from(ModelRun).where(ModelRun.prediction_id == prediction.id)
    ) == 4


def test_evaluation_is_idempotent_for_a_prediction(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    actual = ResultService(session).record(
        match_id=target.id,
        home_score=1,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
        result_source_id=None,
        notes=None,
    )
    service = EvaluationService(session)

    first = service.evaluate(prediction.id, actual.id)
    second = service.evaluate(prediction.id, actual.id)

    assert second.id == first.id


def test_evaluation_summary_apis(client: TestClient, session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    actual = ResultService(session).record(
        match_id=target.id,
        home_score=2,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
        result_source_id=None,
        notes=None,
    )
    EvaluationService(session).evaluate(prediction.id, actual.id)

    overall = client.get("/api/v1/evaluation/summary")
    competition = client.get("/api/v1/evaluation/competition/CSL")

    assert overall.status_code == 200
    assert overall.json()["sample_count"] == 1
    assert competition.status_code == 200
    assert competition.json()["sample_count"] == 1
