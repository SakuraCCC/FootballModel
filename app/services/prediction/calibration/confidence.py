from dataclasses import dataclass
from typing import Literal

from app.services.prediction.features.match_features import MatchFeatures
from app.services.prediction.models.types import EloOutput, ModelOutput
from app.services.prediction.simulation.score_simulator import ScoreSimulationResult


@dataclass(frozen=True)
class ConfidenceAssessment:
    level: Literal["high", "medium", "low"]
    reasons: list[str]


def assess_confidence(
    features: MatchFeatures,
    ensemble: ModelOutput,
    elo: EloOutput,
    simulation: ScoreSimulationResult,
) -> ConfidenceAssessment:
    reasons = list(features.missing_fields)
    if ensemble.model_status == "not_available":
        reasons.append("goal_models_not_available")
    if elo.model_status == "not_available":
        reasons.append("elo_not_available")
    if simulation.low_confidence:
        reasons.append("score_distribution_is_diffuse")
    if features.data_completeness == "low" or ensemble.model_status == "not_available":
        return ConfidenceAssessment("low", reasons)
    if features.data_completeness == "medium" or simulation.low_confidence or elo.model_status == "not_available":
        return ConfidenceAssessment("medium", reasons)
    return ConfidenceAssessment("high", reasons)
