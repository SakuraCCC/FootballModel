from datetime import UTC, datetime

from app.cli import e2e_verify, production_check
from app.core.config import Settings
from app.core.version import FEATURE_VERSION, MODEL_VERSION, POSTER_VERSION, PROMPT_VERSION
from app.models import (
    AutomationRun,
    DailyOperationReport,
    PosterOutput,
    PromptExperiment,
    ReportOutput,
)
from app.services.operations import DailyOperationReportService, PromptExperimentService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting.service import ReportService
from tests.prediction_helpers import create_prediction_dataset
from tests.reporting_helpers import AvailableLLM


def test_production_check_reports_missing_configuration_without_failing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        production_check,
        "get_settings",
        lambda: Settings(database_url="", redis_url="", poster_output_dir=str(tmp_path)),
    )
    monkeypatch.setattr(production_check, "SessionLocal", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    result = production_check.run()
    assert result["status"] == "NOT_READY"
    assert "API_FOOTBALL_KEY" in " ".join(result["missing"])
    assert production_check.main([]) == 0


def test_prediction_and_report_outputs_include_release_metadata(session):
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    assert prediction.model_version == MODEL_VERSION
    assert prediction.feature_version == FEATURE_VERSION
    report = ReportService(session, llm_client=AvailableLLM()).generate(prediction.id, "internal")
    stored = session.get(ReportOutput, report.report_id)
    assert stored is not None
    assert stored.model_version == MODEL_VERSION
    assert stored.poster_version == POSTER_VERSION


def test_prompt_experiment_and_daily_operation_report(session):
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)
    report = ReportOutput(
        prediction_id=prediction.id,
        report_type="internal",
        content="content",
        prompt_version=PROMPT_VERSION,
        status="generated",
        warnings=[],
        created_at=datetime.now(UTC),
    )
    session.add(report)
    session.flush()
    session.add(
        PosterOutput(
            report_id=report.id,
            prediction_id=prediction.id,
            competition_style="CSL",
            file_path="poster.png",
            template_version="v1",
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        AutomationRun(
            match_id=target.id,
            status="completed",
            current_step="archived",
            created_at=datetime.now(UTC),
        )
    )
    session.commit()
    experiment = PromptExperimentService(session).create(
        prompt_name="internal_report", prompt_version=PROMPT_VERSION, change_description="launch baseline"
    )
    assert session.get(PromptExperiment, experiment.id) is not None
    daily = DailyOperationReportService(session).get_or_build(datetime.now(UTC).date())
    assert daily.analysis_match_count == 1
    assert daily.successful_tasks == 1
    assert daily.report_count == 1
    assert daily.poster_count == 1
    assert session.get(DailyOperationReport, daily.id) is not None


def test_daily_report_api_and_e2e_version_fields(client, session):
    response = client.get("/api/v1/dashboard/daily-report")
    assert response.status_code == 200
    assert response.json()["quota_state"] == "unknown"
    result = e2e_verify.run("CSL", "missing", dry_run=True)
    assert result["status"] == "not_executed"
    assert result["version"] == "V3.2"
    assert result["model_version"] == MODEL_VERSION
    assert result["prompt_version"] == PROMPT_VERSION
    assert result["poster_version"] == POSTER_VERSION
