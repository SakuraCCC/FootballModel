from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelRun, ModelVersion, PredictionResult
from app.services.prediction.calibration import assess_confidence
from app.services.prediction.features import FeatureBuilder
from app.services.prediction.models import DixonColesModel, EloModel, EnsembleModel, PoissonModel
from app.services.prediction.models.ensemble import EnsembleOutput
from app.services.prediction.models.types import EloOutput, ModelOutput
from app.services.prediction.simulation import ScoreSimulator


class PredictionPipeline:
    def __init__(self, session: Session) -> None:
        self._session = session

    def run(self, match_id: str) -> PredictionResult:
        features = FeatureBuilder(self._session).build(match_id)
        poisson = PoissonModel().predict(features)
        dixon_coles = DixonColesModel().predict(features)
        elo = EloModel().predict(features)
        ensemble = EnsembleModel().combine(poisson, dixon_coles, elo)
        simulation = ScoreSimulator().simulate(
            ensemble.model_output.score_probabilities, seed=match_id
        )
        confidence = assess_confidence(features, ensemble.model_output, elo, simulation)
        poisson_run = self._save_model_run(features, poisson, confidence.level)
        dixon_run = self._save_model_run(features, dixon_coles, confidence.level)
        elo_run = self._save_elo_run(features, elo, confidence.level)
        ensemble_run = self._save_ensemble_run(features, ensemble, simulation, confidence.level)
        result = self._save_prediction_result(
            features.match_id,
            ensemble,
            poisson,
            dixon_coles,
            elo,
            simulation,
            confidence.level,
            confidence.reasons,
            ensemble_run,
        )
        for model_run in (poisson_run, dixon_run, elo_run, ensemble_run):
            model_run.prediction_id = result.id
        self._session.commit()
        return result

    def _save_model_run(self, features, output: ModelOutput, confidence: str) -> ModelRun:
        version = self._model_version(
            output.model_name, output.model_version, self._description(output.model_name)
        )
        run = ModelRun(
            match_id=features.match_id,
            model_version_id=version.id,
            input_snapshot_id=features.input_snapshot_id,
            output_json=self._model_output_json(output),
            confidence=confidence,
            feature_version="feature_v2",
            data_version=features.input_snapshot_id or "unavailable",
            prompt_version="not_applicable",
            calibration_version="calibration_v1",
        )
        self._session.add(run)
        self._session.flush()
        return run

    def _save_elo_run(self, features, output: EloOutput, confidence: str) -> ModelRun:
        version = self._model_version(
            output.model_name, output.model_version, self._description(output.model_name)
        )
        run = ModelRun(
            match_id=features.match_id,
            model_version_id=version.id,
            input_snapshot_id=features.input_snapshot_id,
            output_json=asdict(output),
            confidence=confidence,
            feature_version="feature_v2",
            data_version=features.input_snapshot_id or "unavailable",
            prompt_version="not_applicable",
            calibration_version="calibration_v1",
        )
        self._session.add(run)
        self._session.flush()
        return run

    def _save_ensemble_run(
        self, features, output: EnsembleOutput, simulation, confidence: str
    ) -> ModelRun:
        model_output = output.model_output
        version = self._model_version(
            model_output.model_name,
            model_output.model_version,
            self._description(model_output.model_name),
        )
        payload = self._model_output_json(model_output)
        payload.update(
            {
                "total_goal_range": output.total_goal_range,
                "btts": output.btts,
                "simulation": {
                    "simulations": simulation.simulations,
                    "scores": [asdict(score) for score in simulation.scores],
                    "low_confidence": simulation.low_confidence,
                },
            }
        )
        run = ModelRun(
            match_id=features.match_id,
            model_version_id=version.id,
            input_snapshot_id=features.input_snapshot_id,
            output_json=payload,
            confidence=confidence,
            feature_version="feature_v2",
            data_version=features.input_snapshot_id or "unavailable",
            prompt_version="not_applicable",
            calibration_version="calibration_v1",
        )
        self._session.add(run)
        self._session.flush()
        return run

    def _save_prediction_result(
        self,
        match_id: str,
        ensemble: EnsembleOutput,
        poisson: ModelOutput,
        dixon_coles: ModelOutput,
        elo: EloOutput,
        simulation,
        confidence: str,
        reasons: list[str],
        ensemble_run: ModelRun,
    ) -> PredictionResult:
        available = ensemble.model_output.model_status == "available"
        scores = simulation.scores
        direction = self._direction(ensemble.model_output) if available else None
        result = PredictionResult(
            match_id=match_id,
            model_run_id=ensemble_run.id,
            status="available" if available else "not_available",
            direction=direction,
            goal_range=ensemble.total_goal_range if available else None,
            btts=ensemble.btts if available else None,
            primary_score=scores[0].score if scores else None,
            stable_score=self._top_score(dixon_coles),
            alternative_score=self._second_score(poisson),
            review_summary={
                "round_1_basic_goal_model": self._top_scores(poisson),
                "round_2_strength_form_home_away": {
                    "dixon_coles": self._top_scores(dixon_coles),
                    "elo": asdict(elo),
                },
                "round_3_fatigue_injuries_data_quality": {
                    "candidate_scores": [asdict(score) for score in scores[:3]],
                    "data_quality_reasons": reasons,
                    "fatigue_used": False,
                    "injuries_used": False,
                },
            },
            confidence=confidence,
        )
        self._session.add(result)
        self._session.flush()
        return result

    def _model_version(self, name: str, version: str, description: str) -> ModelVersion:
        record = self._session.scalar(
            select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version)
        )
        if record is None:
            record = ModelVersion(
                name=name,
                version=version,
                description=description,
                feature_version="feature_v2",
                data_version="snapshot_bound",
                prompt_version="not_applicable",
                calibration_version="calibration_v1",
            )
            self._session.add(record)
            self._session.flush()
        return record

    @staticmethod
    def _model_output_json(output: ModelOutput) -> dict:
        return {
            "model_name": output.model_name,
            "model_version": output.model_version,
            "model_status": output.model_status,
            "reason": output.reason,
            "home_win_probability": output.home_win_probability,
            "draw_probability": output.draw_probability,
            "away_win_probability": output.away_win_probability,
            "expected_home_goals": output.expected_home_goals,
            "expected_away_goals": output.expected_away_goals,
            "score_probabilities": [asdict(score) for score in output.top_scores()],
        }

    @staticmethod
    def _top_scores(output: ModelOutput) -> list[dict]:
        return [asdict(score) for score in output.top_scores(3)]

    @staticmethod
    def _top_score(output: ModelOutput) -> str | None:
        scores = output.top_scores(1)
        return scores[0].score if scores else None

    @staticmethod
    def _second_score(output: ModelOutput) -> str | None:
        scores = output.top_scores(2)
        return scores[1].score if len(scores) > 1 else None

    @staticmethod
    def _direction(output: ModelOutput) -> str:
        values = {
            "home_win_tendency": output.home_win_probability or 0,
            "draw_tendency": output.draw_probability or 0,
            "away_win_tendency": output.away_win_probability or 0,
        }
        return max(values, key=values.get)

    @staticmethod
    def _description(model_name: str) -> str:
        descriptions = {
            "poisson": "Independent Poisson goal model using persisted historical results.",
            "dixon_coles": "Low-score correction applied to the persisted-data Poisson model.",
            "elo": "Elo strength calculation from persisted chronological results.",
            "ensemble": "Combination of Poisson, Dixon-Coles, and available Elo adjustment.",
        }
        return descriptions[model_name]
