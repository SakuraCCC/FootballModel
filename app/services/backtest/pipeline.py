from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActualResult, Competition, Match
from app.services.evaluation import EvaluationService
from app.services.prediction.pipeline import PredictionPipeline


@dataclass(frozen=True)
class BacktestResult:
    processed: int
    evaluated: int
    skipped_not_available: int
    prediction_ids: list[str]


class BacktestPipeline:
    """Replays completed matches using only data available before each kickoff."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def run(
        self,
        *,
        competition_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BacktestResult:
        competition = self._session.scalar(
            select(Competition).where(Competition.code == competition_code.upper())
        )
        if competition is None:
            raise ValueError("Competition was not found")
        statement = (
            select(Match, ActualResult)
            .join(ActualResult, ActualResult.match_id == Match.id)
            .where(
                Match.competition_id == competition.id,
                Match.kickoff_at.is_not(None),
                ActualResult.completed_at.is_not(None),
            )
            .order_by(Match.kickoff_at.asc())
        )
        if start_date is not None:
            statement = statement.where(Match.kickoff_at >= start_date)
        if end_date is not None:
            statement = statement.where(Match.kickoff_at < end_date)
        processed = 0
        evaluated = 0
        skipped = 0
        prediction_ids: list[str] = []
        # Materialize before the prediction pipeline commits each model run.
        # This keeps the historical input set stable throughout a replay.
        historical_matches = list(self._session.execute(statement))
        for match, actual in historical_matches:
            processed += 1
            prediction = PredictionPipeline(self._session).run(match.id)
            prediction_ids.append(prediction.id)
            if prediction.status != "available":
                skipped += 1
                continue
            EvaluationService(self._session).evaluate(prediction.id, actual.id)
            evaluated += 1
        return BacktestResult(processed, evaluated, skipped, prediction_ids)
