from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models import PosterOutput, ReportOutput
from app.services.scheduler import AutomationPipeline, MatchScanner
from tests.prediction_helpers import create_prediction_dataset


def test_match_scanner_finds_only_24_to_72_hour_fixtures(session: Session) -> None:
    target = create_prediction_dataset(session)

    matches = MatchScanner(session).scan(now=datetime(2026, 7, 30, 12, tzinfo=UTC))

    assert [item.match_id for item in matches] == [target.id]


def test_automation_pipeline_records_completed_lifecycle(session: Session, monkeypatch) -> None:
    target = create_prediction_dataset(session)

    class FakeReportService:
        def __init__(self, db_session: Session) -> None:
            self._session = db_session

        def generate(self, prediction_id: str, report_type: str) -> SimpleNamespace:
            report = ReportOutput(
                prediction_id=prediction_id,
                report_type=report_type,
                content="approved",
                prompt_version="test",
                llm_model="test",
                status="generated",
                warnings=[],
            )
            self._session.add(report)
            self._session.commit()
            self._session.refresh(report)
            return SimpleNamespace(report_id=report.id, status=report.status)

    class FakePosterService:
        def __init__(self, db_session: Session) -> None:
            self._session = db_session

        def generate(self, report_id: str) -> SimpleNamespace:
            report = self._session.get(ReportOutput, report_id)
            poster = PosterOutput(
                report_id=report.id,
                prediction_id=report.prediction_id,
                competition_style="CSL",
                file_path="",
                template_version="test",
            )
            self._session.add(poster)
            self._session.commit()
            self._session.refresh(poster)
            return SimpleNamespace(file_path=f"generated/posters/{poster.id}.png")

    import app.services.scheduler.automation as automation_module

    monkeypatch.setattr(automation_module, "ReportService", FakeReportService)
    monkeypatch.setattr(automation_module, "PosterService", FakePosterService)

    run = AutomationPipeline(session).run(target.id, task_id="task-1", retry_count=2)

    assert run.status == "completed"
    assert run.current_step == "completed"
    assert run.retry_count == 2
    assert run.analysis_job_id is not None
    assert run.prediction_id is not None
    assert run.report_id is not None
    assert run.poster_id is not None
