from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.version import DATA_VERSION, FEATURE_VERSION, MODEL_VERSION, POSTER_VERSION
from app.models import (
    ActualResult,
    Match,
    ModelRun,
    PosterOutput,
    PredictionArchive,
    PredictionResult,
    ReportOutput,
)


class PredictionArchiveService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def archive(self, prediction_id: str) -> PredictionArchive:
        prediction = self._session.get(PredictionResult, prediction_id)
        if prediction is None:
            raise ValueError("Prediction was not found")
        match = self._session.get(Match, prediction.match_id)
        model_run = self._session.get(ModelRun, prediction.model_run_id)
        if match is None or model_run is None:
            raise ValueError("Prediction inputs were not found")
        report = self._session.scalar(
            select(ReportOutput)
            .where(ReportOutput.prediction_id == prediction.id)
            .order_by(ReportOutput.created_at.desc())
        )
        poster = self._session.scalar(
            select(PosterOutput)
            .where(PosterOutput.prediction_id == prediction.id)
            .order_by(PosterOutput.created_at.desc())
        )
        actual = self._session.scalar(select(ActualResult).where(ActualResult.match_id == match.id))
        archive = self._session.scalar(
            select(PredictionArchive).where(PredictionArchive.prediction_id == prediction.id)
        )
        values = {
            "input_summary": {
                "match_id": match.id,
                "competition_id": match.competition_id,
                "kickoff_at": match.kickoff_at.isoformat() if match.kickoff_at else None,
                "input_snapshot_id": model_run.input_snapshot_id,
                "data_version": model_run.data_version or DATA_VERSION,
            },
            "model_output": model_run.output_json,
            "report_content": report.content if report else None,
            "poster_path": poster.file_path if poster else None,
            "actual_result": {
                "home_score": actual.home_score,
                "away_score": actual.away_score,
                "result": actual.result,
                "completed_at": actual.completed_at.isoformat() if actual.completed_at else None,
            }
            if actual
            else None,
            "archived_at": datetime.now(UTC),
            "model_version": prediction.model_version or MODEL_VERSION,
            "feature_version": prediction.feature_version or FEATURE_VERSION,
            "data_version": prediction.data_version or DATA_VERSION,
            "prompt_version": report.prompt_version if report else "not_applicable",
            "poster_version": poster.poster_version if poster else POSTER_VERSION,
        }
        if archive is None:
            archive = PredictionArchive(prediction_id=prediction.id, **values)
            self._session.add(archive)
        else:
            for key, value in values.items():
                setattr(archive, key, value)
        self._session.commit()
        self._session.refresh(archive)
        return archive
