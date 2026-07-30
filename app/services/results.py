from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import ActualResult, Match, PredictionResult
from app.services.archive import PredictionArchiveService


class ResultService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        match_id: str,
        home_score: int,
        away_score: int,
        completed_at: datetime | None,
        result_source_id: str | None,
        notes: str | None,
    ) -> ActualResult:
        if self._session.get(Match, match_id) is None:
            raise ValueError("Match was not found")
        actual = self._session.query(ActualResult).filter(ActualResult.match_id == match_id).one_or_none()
        if actual is None:
            actual = ActualResult(match_id=match_id, home_score=home_score, away_score=away_score)
            self._session.add(actual)
        actual.home_score = home_score
        actual.away_score = away_score
        actual.result = self._result(home_score, away_score)
        actual.total_goals = home_score + away_score
        actual.btts_result = home_score > 0 and away_score > 0
        actual.completed_at = completed_at or datetime.now(UTC)
        actual.result_source_id = result_source_id
        actual.notes = notes
        self._session.commit()
        prediction_ids = self._session.scalars(
            self._session.query(PredictionResult.id).filter(PredictionResult.match_id == match_id).statement
        )
        for prediction_id in prediction_ids:
            PredictionArchiveService(self._session).archive(prediction_id)
        return actual

    @staticmethod
    def _result(home_score: int, away_score: int) -> str:
        if home_score > away_score:
            return "home_win"
        if home_score < away_score:
            return "away_win"
        return "draw"
