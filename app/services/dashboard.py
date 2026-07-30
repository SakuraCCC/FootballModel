from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    ContentPublishRecord,
    Match,
    PosterOutput,
    PredictionResult,
    ReportOutput,
)
from app.services.evaluation import EvaluationService


class DashboardService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def summary(self) -> dict:
        competition_counts = self._session.execute(
            select(Competition.code, func.count(PredictionResult.id))
            .join(Match, Match.competition_id == Competition.id)
            .join(PredictionResult, PredictionResult.match_id == Match.id)
            .group_by(Competition.code)
            .order_by(Competition.code)
        )
        return {
            "total_predictions": self._count(PredictionResult),
            "total_reports": self._count(ReportOutput),
            "total_posters": self._count(PosterOutput),
            "competition_counts": [
                {"competition_code": code, "prediction_count": count}
                for code, count in competition_counts
            ],
        }

    def content_assets(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        competition_code: str | None = None,
        match_id: str | None = None,
    ) -> dict:
        statement = (
            select(ReportOutput, PredictionResult, Match, Competition)
            .join(PredictionResult, PredictionResult.id == ReportOutput.prediction_id)
            .join(Match, Match.id == PredictionResult.match_id)
            .join(Competition, Competition.id == Match.competition_id)
        )
        if start_date:
            statement = statement.where(Match.kickoff_at >= datetime.combine(start_date, time.min, UTC))
        if end_date:
            statement = statement.where(Match.kickoff_at < datetime.combine(end_date, time.min, UTC))
        if competition_code:
            statement = statement.where(Competition.code == competition_code.upper())
        if match_id:
            statement = statement.where(Match.id == match_id)
        rows = list(self._session.execute(statement))
        report_ids = [report.id for report, _prediction, _match, _competition in rows]
        poster_count = (
            self._session.scalar(select(func.count()).select_from(PosterOutput).where(PosterOutput.report_id.in_(report_ids)))
            if report_ids
            else 0
        )
        published_count = (
            self._session.scalar(
                select(func.count())
                .select_from(ContentPublishRecord)
                .where(ContentPublishRecord.report_id.in_(report_ids), ContentPublishRecord.publish_time.is_not(None))
            )
            if report_ids
            else 0
        )
        return {
            "report_count": len(report_ids),
            "poster_count": poster_count or 0,
            "published_count": published_count or 0,
            "unpublished_count": len(report_ids) - (published_count or 0),
        }

    def model_performance(self) -> dict:
        return EvaluationService(self._session).summary()

    def _count(self, model) -> int:
        return self._session.scalar(select(func.count()).select_from(model)) or 0
