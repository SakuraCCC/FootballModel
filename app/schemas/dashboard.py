from typing import Any

from pydantic import BaseModel


class CompetitionCount(BaseModel):
    competition_code: str
    prediction_count: int


class DashboardSummaryRead(BaseModel):
    total_predictions: int
    total_reports: int
    total_posters: int
    competition_counts: list[CompetitionCount]
    today_pending_matches: int
    today_completed_automations: int


class ContentAssetSummaryRead(BaseModel):
    report_count: int
    poster_count: int
    published_count: int
    unpublished_count: int


class ModelPerformanceDashboardRead(BaseModel):
    sample_count: int
    direction_accuracy: float | None
    score_exact_accuracy: float | None
    score_top3_accuracy: float | None
    goal_range_accuracy: float | None
    btts_accuracy: float | None
    log_loss: float | None
    brier_score: float | None
    models: list[dict[str, Any]]
