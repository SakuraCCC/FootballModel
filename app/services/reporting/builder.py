from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    Match,
    ModelRun,
    PredictionEvaluation,
    PredictionResult,
    RawDataSnapshot,
    Team,
)
from app.services.reporting.schemas import ReportContext, ReportFact, SourceReference


class ReportContextBuilder:
    """Build a source-preserving report context from persisted Phase 3–4.5 data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def build(self, prediction_id: str) -> ReportContext:
        prediction = self._session.get(PredictionResult, prediction_id)
        if prediction is None:
            raise ValueError("Prediction was not found")
        match = self._session.get(Match, prediction.match_id)
        if match is None:
            raise ValueError("Prediction match was not found")
        competition = self._session.get(Competition, match.competition_id)
        home_team = self._session.get(Team, match.home_team_id) if match.home_team_id else None
        away_team = self._session.get(Team, match.away_team_id) if match.away_team_id else None
        model_runs = list(
            self._session.scalars(select(ModelRun).where(ModelRun.prediction_id == prediction.id))
        )
        snapshots = self._snapshots(model_runs)
        snapshot_ids = [snapshot.id for snapshot in snapshots]
        fact = ReportFact(
            label="match",
            value=f"{home_team.canonical_name if home_team else None} vs "
            f"{away_team.canonical_name if away_team else None}",
            certainty=self._certainty(match.certainty),
            source_snapshot_ids=snapshot_ids,
        )
        evaluation = self._session.scalar(
            select(PredictionEvaluation).where(PredictionEvaluation.prediction_id == prediction.id)
        )
        return ReportContext(
            prediction_id=prediction.id,
            match_info={
                "match_id": match.id,
                "competition_code": competition.code if competition else None,
                "competition_name": competition.name if competition else None,
                "home_team": home_team.canonical_name if home_team else None,
                "away_team": away_team.canonical_name if away_team else None,
                "kickoff_at": match.kickoff_at,
                "certainty": self._certainty(match.certainty),
            },
            confirmed_facts=[fact] if fact.certainty in {"official", "confirmed"} else [],
            reported_information=[fact] if fact.certainty == "reported" else [],
            model_prediction={
                "status": prediction.status,
                "direction": prediction.direction,
                "goal_range": prediction.goal_range,
                "btts": prediction.btts,
                "primary_score": prediction.primary_score,
                "stable_score": prediction.stable_score,
                "alternative_score": prediction.alternative_score,
                "model_output": self._model_output(prediction),
            },
            score_review=prediction.review_summary,
            risk_warning=self._risk_warnings(prediction, snapshots),
            data_completeness=self._data_completeness(prediction),
            confidence=prediction.confidence,
            source_snapshots=[
                SourceReference(
                    snapshot_id=snapshot.id,
                    provider=snapshot.provider,
                    endpoint=snapshot.endpoint,
                    retrieved_at=snapshot.retrieved_at,
                )
                for snapshot in snapshots
            ],
            evaluation_results=self._evaluation_payload(evaluation),
        )

    def _snapshots(self, model_runs: list[ModelRun]) -> list[RawDataSnapshot]:
        snapshot_ids = {run.input_snapshot_id for run in model_runs if run.input_snapshot_id}
        if not snapshot_ids:
            return []
        return list(
            self._session.scalars(
                select(RawDataSnapshot)
                .where(RawDataSnapshot.id.in_(snapshot_ids))
                .order_by(RawDataSnapshot.retrieved_at.asc())
            )
        )

    def _model_output(self, prediction: PredictionResult) -> dict[str, Any]:
        run = self._session.get(ModelRun, prediction.model_run_id)
        return run.output_json if run is not None else {}

    @staticmethod
    def _certainty(value: str) -> str:
        return value if value in {"official", "confirmed", "reported", "predicted", "unavailable"} else "unavailable"

    @staticmethod
    def _risk_warnings(prediction: PredictionResult, snapshots: list[RawDataSnapshot]) -> list[str]:
        warnings: list[str] = []
        if prediction.status != "available":
            warnings.append("预测数据不足，模型结果不可用。")
        if not snapshots:
            warnings.append("缺少可追溯的原始数据快照。")
        warnings.append("模型方向和比分为模型推断，不是确定事实。")
        return warnings

    @staticmethod
    def _data_completeness(prediction: PredictionResult) -> str:
        reasons = prediction.review_summary.get("round_3_fatigue_injuries_data_quality", {}).get(
            "data_quality_reasons", []
        )
        return "medium" if reasons else "high"

    @staticmethod
    def _evaluation_payload(evaluation: PredictionEvaluation | None) -> dict[str, Any] | None:
        if evaluation is None:
            return None
        return {
            "direction_correct": evaluation.direction_correct,
            "score_exact_correct": evaluation.score_exact_correct,
            "score_top3_correct": evaluation.score_top3_correct,
            "goal_range_correct": evaluation.goal_range_correct,
            "btts_correct": evaluation.btts_correct,
            "log_loss": evaluation.log_loss,
            "brier_score": evaluation.brier_score,
            "evaluated_at": evaluation.evaluated_at,
        }
