from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ActualResult,
    Competition,
    Match,
    ModelPerformance,
    ModelRun,
    ModelVersion,
    PredictionEvaluation,
    PredictionResult,
)
from app.services.evaluation.metrics import output_direction, probability_metrics, result_direction


class EvaluationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(self, prediction_id: str, actual_result_id: str) -> PredictionEvaluation:
        existing = self._session.scalar(
            select(PredictionEvaluation).where(PredictionEvaluation.prediction_id == prediction_id)
        )
        if existing is not None:
            return existing
        prediction = self._session.get(PredictionResult, prediction_id)
        actual = self._session.get(ActualResult, actual_result_id)
        if prediction is None or actual is None:
            raise ValueError("Prediction or actual result was not found")
        if prediction.status != "available":
            raise ValueError("A not_available prediction cannot be evaluated")
        output = self._model_output(prediction)
        actual_direction = result_direction(actual.home_score, actual.away_score)
        metrics = probability_metrics(output, actual_direction)
        evaluation = PredictionEvaluation(
            prediction_id=prediction.id,
            actual_result_id=actual.id,
            direction_correct=prediction.direction == actual_direction,
            score_exact_correct=prediction.primary_score == f"{actual.home_score}-{actual.away_score}",
            score_top3_correct=self._score_in_top3(output, actual.home_score, actual.away_score),
            goal_range_correct=self._goal_range_contains(prediction.goal_range, actual.home_score + actual.away_score),
            btts_correct=self._btts_correct(prediction.btts, actual.home_score, actual.away_score),
            log_loss=metrics.log_loss if metrics else None,
            brier_score=metrics.brier_score if metrics else None,
            evaluated_at=datetime.now(UTC),
        )
        self._session.add(evaluation)
        self._session.flush()
        match = self._session.get(Match, prediction.match_id)
        if match is not None:
            self.refresh_model_performance(match.competition_id)
        self._session.commit()
        return evaluation

    def refresh_model_performance(self, competition_id: str) -> None:
        statement = (
            select(ModelRun, PredictionEvaluation, ActualResult, Match)
            .join(PredictionEvaluation, PredictionEvaluation.prediction_id == ModelRun.prediction_id)
            .join(ActualResult, ActualResult.id == PredictionEvaluation.actual_result_id)
            .join(Match, Match.id == ModelRun.match_id)
            .where(Match.competition_id == competition_id)
        )
        grouped: dict[str, list[tuple[ModelRun, ActualResult]]] = {}
        for model_run, _evaluation, actual, _match in self._session.execute(statement):
            if model_run.output_json.get("model_status") != "available":
                continue
            if probability_metrics(model_run.output_json, result_direction(actual.home_score, actual.away_score)) is None:
                continue
            grouped.setdefault(model_run.model_version_id, []).append((model_run, actual))
        for version_id, entries in grouped.items():
            correctness = []
            log_losses = []
            brier_scores = []
            for model_run, actual in entries:
                actual_direction = result_direction(actual.home_score, actual.away_score)
                correctness.append(output_direction(model_run.output_json) == actual_direction)
                metrics = probability_metrics(model_run.output_json, actual_direction)
                if metrics is not None:
                    log_losses.append(metrics.log_loss)
                    brier_scores.append(metrics.brier_score)
            performance = self._session.scalar(
                select(ModelPerformance).where(
                    ModelPerformance.model_version_id == version_id,
                    ModelPerformance.competition_id == competition_id,
                )
            )
            if performance is None:
                performance = ModelPerformance(
                    model_version_id=version_id,
                    competition_id=competition_id,
                    sample_count=len(entries),
                    accuracy=sum(correctness) / len(correctness),
                    log_loss=sum(log_losses) / len(log_losses),
                    brier_score=sum(brier_scores) / len(brier_scores),
                    calculated_at=datetime.now(UTC),
                )
                self._session.add(performance)
            else:
                performance.sample_count = len(entries)
                performance.accuracy = sum(correctness) / len(correctness)
                performance.log_loss = sum(log_losses) / len(log_losses)
                performance.brier_score = sum(brier_scores) / len(brier_scores)
                performance.calculated_at = datetime.now(UTC)

    def summary(self, competition_code: str | None = None) -> dict:
        statement = (
            select(PredictionEvaluation, PredictionResult, Match)
            .join(PredictionResult, PredictionResult.id == PredictionEvaluation.prediction_id)
            .join(Match, Match.id == PredictionResult.match_id)
        )
        competition_id = None
        if competition_code is not None:
            competition = self._session.scalar(
                select(Competition).where(Competition.code == competition_code.upper())
            )
            if competition is None:
                raise ValueError("Competition was not found")
            competition_id = competition.id
            statement = statement.where(Match.competition_id == competition_id)
        rows = list(self._session.execute(statement))
        evaluations = [row[0] for row in rows]
        sample_count = len(evaluations)
        performances = self._model_performance(competition_id)
        return {
            "sample_count": sample_count,
            "direction_accuracy": self._boolean_average(evaluations, "direction_correct"),
            "score_exact_accuracy": self._boolean_average(evaluations, "score_exact_correct"),
            "score_top3_accuracy": self._boolean_average(evaluations, "score_top3_correct"),
            "goal_range_accuracy": self._boolean_average(evaluations, "goal_range_correct"),
            "btts_accuracy": self._boolean_average(evaluations, "btts_correct"),
            "log_loss": self._average(evaluations, "log_loss"),
            "brier_score": self._average(evaluations, "brier_score"),
            "models": performances,
        }

    def _model_performance(self, competition_id: str | None) -> list[dict]:
        statement = (
            select(ModelPerformance, ModelVersion)
            .join(ModelVersion, ModelVersion.id == ModelPerformance.model_version_id)
            .order_by(ModelVersion.name)
        )
        if competition_id is not None:
            statement = statement.where(ModelPerformance.competition_id == competition_id)
        return [
            {
                "model_name": version.name,
                "model_version": version.version,
                "sample_count": performance.sample_count,
                "accuracy": performance.accuracy,
                "log_loss": performance.log_loss,
                "brier_score": performance.brier_score,
            }
            for performance, version in self._session.execute(statement)
        ]

    @staticmethod
    def _boolean_average(entries: list[PredictionEvaluation], attribute: str) -> float | None:
        if not entries:
            return None
        return sum(bool(getattr(entry, attribute)) for entry in entries) / len(entries)

    @staticmethod
    def _average(entries: list[PredictionEvaluation], attribute: str) -> float | None:
        values = [getattr(entry, attribute) for entry in entries if getattr(entry, attribute) is not None]
        return sum(values) / len(values) if values else None

    def _model_output(self, prediction: PredictionResult) -> dict:
        model_run = self._session.get(ModelRun, prediction.model_run_id)
        return model_run.output_json if model_run is not None else {}

    def _score_in_top3(self, output: dict, home_score: int, away_score: int) -> bool:
        actual = (home_score, away_score)
        scores = output.get("score_probabilities", [])
        return actual in [
            (item.get("home_goals"), item.get("away_goals")) for item in scores[:3] if isinstance(item, dict)
        ]

    @staticmethod
    def _goal_range_contains(goal_range: str | None, total_goals: int) -> bool:
        if goal_range is None:
            return False
        try:
            low, high = (int(value) for value in goal_range.split("-", maxsplit=1))
        except ValueError:
            return False
        return low <= total_goals <= high

    @staticmethod
    def _btts_correct(prediction_btts: str | None, home_score: int, away_score: int) -> bool:
        if prediction_btts not in {"likely", "unlikely"}:
            return False
        actual = home_score > 0 and away_score > 0
        return (prediction_btts == "likely") == actual
