from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActualResult, ConfidenceCalibration, Match, ModelRun, PredictionEvaluation
from app.services.evaluation.metrics import output_direction, result_direction


class CalibrationService:
    """Persist reliability buckets from evaluated, pre-existing model runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def refresh(self, competition_id: str | None = None) -> list[ConfidenceCalibration]:
        statement = (
            select(ModelRun, PredictionEvaluation, ActualResult, Match)
            .join(
                PredictionEvaluation, PredictionEvaluation.prediction_id == ModelRun.prediction_id
            )
            .join(ActualResult, ActualResult.id == PredictionEvaluation.actual_result_id)
            .join(Match, Match.id == ModelRun.match_id)
        )
        if competition_id:
            statement = statement.where(Match.competition_id == competition_id)
        groups: dict[tuple[str, str, str], list[tuple[float, bool]]] = defaultdict(list)
        for run, _evaluation, actual, match in self._session.execute(statement):
            probabilities = [
                run.output_json.get(key)
                for key in ("home_win_probability", "draw_probability", "away_win_probability")
            ]
            if any(value is None for value in probabilities):
                continue
            probability = max(float(value) for value in probabilities)
            is_correct = output_direction(run.output_json) == result_direction(
                actual.home_score, actual.away_score
            )
            groups[(run.model_version_id, match.competition_id, self._bucket(probability))].append(
                (probability, is_correct)
            )
        records = []
        for (version_id, comp_id, bucket), entries in groups.items():
            observed = sum(correct for _probability, correct in entries) / len(entries)
            mean_predicted = sum(probability for probability, _correct in entries) / len(entries)
            error = abs(mean_predicted - observed)
            record = self._session.scalar(
                select(ConfidenceCalibration).where(
                    ConfidenceCalibration.model_version_id == version_id,
                    ConfidenceCalibration.competition_id == comp_id,
                    ConfidenceCalibration.probability_bin == bucket,
                )
            )
            if record is None:
                record = ConfidenceCalibration(
                    model_version_id=version_id,
                    competition_id=comp_id,
                    probability_bin=bucket,
                    sample_count=len(entries),
                    observed_frequency=observed,
                    calibration_error=error,
                    reliability=1 - error,
                    calculated_at=datetime.now(UTC),
                )
                self._session.add(record)
            else:
                record.sample_count, record.observed_frequency = len(entries), observed
                record.calibration_error, record.reliability = error, 1 - error
                record.calculated_at = datetime.now(UTC)
            records.append(record)
        self._session.commit()
        return records

    @staticmethod
    def _bucket(probability: float) -> str:
        lower = min(0.9, int(probability * 10) / 10)
        return f"{lower:.1f}-{lower + 0.1:.1f}"
