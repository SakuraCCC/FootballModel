from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_health_service
from app.main import create_app
from app.models import (
    ActualResult,
    AutomationRun,
    DataSource,
    PredictionArchive,
)
from app.schemas.health import DependencyStatus, SchedulerHealthResponse
from app.services.archive import PredictionArchiveService
from app.services.evaluation import CalibrationService, EvaluationService
from app.services.prediction.features import calculate_player_importance
from app.services.prediction.pipeline import PredictionPipeline
from app.services.results import ResultService
from tests.prediction_helpers import create_prediction_dataset


class HealthySchedulerService:
    def scheduler_health(self) -> SchedulerHealthResponse:
        return SchedulerHealthResponse(
            status="ok",
            database=DependencyStatus(status="ok"),
            redis=DependencyStatus(status="ok"),
            beat_status="ok",
            last_task_execution=datetime.now(UTC).isoformat(),
        )


def test_scheduler_health_endpoint() -> None:
    application = create_app()
    application.dependency_overrides[get_health_service] = HealthySchedulerService
    with TestClient(application) as client:
        response = client.get("/scheduler-health")
    assert response.status_code == 200
    assert response.json()["beat_status"] == "ok"


def test_provider_status_marks_missing_key_unavailable(
    client: TestClient, session: Session, monkeypatch
) -> None:
    source = DataSource(
        name="API-Football",
        source_name="API-Football",
        source_type="api",
        source_tier="secondary",
        reliability_level="reported",
        metadata_={},
    )
    session.add(source)
    session.commit()
    monkeypatch.setattr(
        "app.services.provider_health.service.get_settings",
        lambda: type("Settings", (), {"api_football_key": None})(),
    )

    response = client.get("/api/v1/providers/status")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "unavailable"


def test_automation_failures_endpoint_returns_failure_metadata(
    client: TestClient, session: Session
) -> None:
    target = create_prediction_dataset(session)
    session.add(
        AutomationRun(
            match_id=target.id,
            status="failed",
            current_step="report",
            retry_count=2,
            failure_reason="LLM unavailable",
            failed_step="report",
        )
    )
    session.commit()

    response = client.get("/api/v1/automation/failures")

    assert response.status_code == 200
    assert response.json()[0]["failed_step"] == "report"
    assert response.json()[0]["failure_reason"] == "LLM unavailable"


def test_calibration_and_prediction_archive(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    actual = ActualResult(
        match_id=target.id,
        home_score=2,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
    )
    session.add(actual)
    session.commit()
    EvaluationService(session).evaluate(prediction.id, actual.id)

    calibrations = CalibrationService(session).refresh()
    archive = PredictionArchiveService(session).archive(prediction.id)

    assert calibrations
    assert all(item.reliability is not None for item in calibrations)
    assert archive.actual_result == {
        "home_score": 2,
        "away_score": 1,
        "result": None,
        "completed_at": actual.completed_at.isoformat(),
    }
    assert session.get(PredictionArchive, archive.id) is not None


def test_player_importance_requires_provider_minutes() -> None:
    assert calculate_player_importance(
        minutes_played=None, goals=5, assists=1, position="forward"
    ) == (None, None)
    score, weight = calculate_player_importance(
        minutes_played=900, goals=5, assists=2, position="forward"
    )
    assert score is not None and score > 0
    assert weight == 1.15


def test_result_record_refreshes_existing_prediction_archive(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    PredictionArchiveService(session).archive(prediction.id)

    ResultService(session).record(
        match_id=target.id,
        home_score=1,
        away_score=0,
        completed_at=target.kickoff_at,
        result_source_id=None,
        notes=None,
    )

    assert (
        session.get(
            PredictionArchive,
            session.query(PredictionArchive).filter_by(prediction_id=prediction.id).one().id,
        ).actual_result["result"]
        == "home_win"
    )


def test_model_performance_supports_model_and_time_filters(
    client: TestClient, session: Session
) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    actual = ActualResult(
        match_id=target.id,
        home_score=2,
        away_score=1,
        completed_at=target.kickoff_at + timedelta(hours=2),
    )
    session.add(actual)
    session.commit()
    EvaluationService(session).evaluate(prediction.id, actual.id)

    response = client.get(
        "/api/v1/evaluation/model-performance?competition_code=CSL&model_name=poisson&start_date=2026-07-01&end_date=2026-09-01"
    )

    assert response.status_code == 200
    assert response.json()[0]["model_name"] == "poisson"
