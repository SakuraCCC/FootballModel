import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisJob, AnalysisJobMatch, AutomationRun, Competition, Match, Team
from app.services.posters import PosterService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting import ReportService

logger = logging.getLogger(__name__)


class AutomationPipeline:
    """Persist and execute the prediction → report → poster lifecycle for one match."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def run(self, match_id: str, *, task_id: str | None = None, retry_count: int = 0) -> AutomationRun:
        run = self._get_or_create_run(match_id)
        try:
            match, competition, home, away = self._match_context(match_id)
            self._update(run, "running", "create_analysis_job", task_id=task_id, retry_count=retry_count)
            if run.analysis_job_id is None:
                job = AnalysisJob(
                    competition_name=competition.name,
                    match_date=match.kickoff_at.date(),
                    model_version="Sakura AI足球预测系统 V2.0",
                    poster_style=competition.code.lower(),
                    watermark="Sakura Football Model V2.0",
                    status="running",
                    current_step="automation_prediction",
                    matches=[
                        AnalysisJobMatch(
                            home_team=home.canonical_name if home else "未提供",
                            away_team=away.canonical_name if away else "未提供",
                        )
                    ],
                )
                self._session.add(job)
                self._session.flush()
                run.analysis_job_id = job.id
                self._session.commit()
            self._update(run, "running", "prediction", task_id=task_id, retry_count=retry_count)
            prediction = PredictionPipeline(self._session).run(match_id)
            run.prediction_id = prediction.id
            if prediction.status != "available":
                raise RuntimeError("Prediction is not available for automated reporting")
            self._session.commit()
            self._update(run, "running", "report", task_id=task_id, retry_count=retry_count)
            report = ReportService(self._session).generate(prediction.id, "xiaohongshu")
            run.report_id = report.report_id
            if report.status != "generated":
                raise RuntimeError(f"Report generation status: {report.status}")
            self._session.commit()
            self._update(run, "running", "poster", task_id=task_id, retry_count=retry_count)
            poster = PosterService(self._session).generate(report.report_id)
            run.poster_id = self._poster_id(poster.file_path)
            job = self._session.get(AnalysisJob, run.analysis_job_id)
            if job is not None:
                job.status = "completed"
                job.current_step = "completed"
            self._update(run, "completed", "completed", task_id=task_id, retry_count=retry_count)
            return run
        except Exception as error:
            self._session.rollback()
            run = self._get_or_create_run(match_id)
            self._update(
                run,
                "failed",
                "failed",
                task_id=task_id,
                retry_count=retry_count,
                error_message=str(error)[:1000],
            )
            logger.exception("automation_pipeline_failed match_id=%s retry_count=%s", match_id, retry_count)
            raise

    def _get_or_create_run(self, match_id: str) -> AutomationRun:
        run = self._session.scalar(select(AutomationRun).where(AutomationRun.match_id == match_id))
        if run is None:
            run = AutomationRun(match_id=match_id)
            self._session.add(run)
            self._session.commit()
        return run

    def _match_context(self, match_id: str):
        match = self._session.get(Match, match_id)
        if match is None or match.kickoff_at is None:
            raise ValueError("Match or kickoff time was not found")
        competition = self._session.get(Competition, match.competition_id)
        if competition is None:
            raise ValueError("Match competition was not found")
        home = self._session.get(Team, match.home_team_id) if match.home_team_id else None
        away = self._session.get(Team, match.away_team_id) if match.away_team_id else None
        return match, competition, home, away

    def _update(
        self,
        run: AutomationRun,
        status: str,
        step: str,
        *,
        task_id: str | None,
        retry_count: int,
        error_message: str | None = None,
    ) -> None:
        run.status = status
        run.current_step = step
        run.task_id = task_id
        run.retry_count = retry_count
        run.error_message = error_message
        self._session.commit()

    @staticmethod
    def _poster_id(file_path: str) -> str:
        from pathlib import Path

        return Path(file_path).stem
