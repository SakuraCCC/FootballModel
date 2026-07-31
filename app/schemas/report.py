from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    prediction_id: str = Field(min_length=1, max_length=36)
    report_type: Literal["internal", "xiaohongshu"] = "internal"


class ReportGenerateResponse(BaseModel):
    report_id: str
    status: Literal["generated", "warning", "llm_unavailable"]
    prompt_version: str | None = None
    model_version: str | None = None


class ReportRead(BaseModel):
    id: str
    prediction_id: str
    report_type: Literal["internal", "xiaohongshu"]
    content: str | None
    prompt_version: str
    llm_model: str | None
    status: Literal["generated", "warning", "llm_unavailable"]
    warnings: list[str]
    review_status: Literal["draft", "fact_checked", "approved", "rejected"]
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime
    model_version: str | None = None
    feature_version: str | None = None
    data_version: str | None = None
    poster_version: str | None = None


class ReportReviewRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
