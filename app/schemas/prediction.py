from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictionRunRequest(BaseModel):
    match_id: str = Field(min_length=1, max_length=36)


class PredictionRunResponse(BaseModel):
    prediction_id: str
    status: str


class PredictionRead(BaseModel):
    id: str
    match_id: str
    model_run_id: str
    status: str
    direction: str | None
    goal_range: str | None
    btts: str | None
    primary_score: str | None
    stable_score: str | None
    alternative_score: str | None
    review_summary: dict[str, Any]
    confidence: str
    created_at: datetime
    model_output: dict[str, Any]
