from datetime import date, datetime

from pydantic import BaseModel, Field


class ActualResultCreate(BaseModel):
    match_id: str = Field(min_length=1, max_length=36)
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    completed_at: datetime | None = None
    result_source_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ActualResultRead(BaseModel):
    id: str
    match_id: str
    home_score: int
    away_score: int
    result: str | None
    total_goals: int | None
    btts_result: bool | None
    completed_at: datetime | None


class EvaluationRunRequest(BaseModel):
    prediction_id: str
    actual_result_id: str


class EvaluationRead(BaseModel):
    id: str
    prediction_id: str
    actual_result_id: str
    direction_correct: bool
    score_exact_correct: bool
    score_top3_correct: bool
    goal_range_correct: bool
    btts_correct: bool
    log_loss: float | None
    brier_score: float | None
    evaluated_at: datetime


class ModelPerformanceRead(BaseModel):
    model_name: str
    model_version: str
    sample_count: int
    accuracy: float | None
    log_loss: float | None
    brier_score: float | None


class EvaluationSummaryRead(BaseModel):
    sample_count: int
    direction_accuracy: float | None
    score_exact_accuracy: float | None
    score_top3_accuracy: float | None
    goal_range_accuracy: float | None
    btts_accuracy: float | None
    log_loss: float | None
    brier_score: float | None
    models: list[ModelPerformanceRead]


class BacktestRunRequest(BaseModel):
    competition_code: str = Field(min_length=1, max_length=32)
    start_date: date | None = None
    end_date: date | None = None


class BacktestRunResponse(BaseModel):
    processed: int
    evaluated: int
    skipped_not_available: int
    prediction_ids: list[str]
