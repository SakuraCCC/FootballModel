from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    prediction_id: str = Field(min_length=1, max_length=36)
    report_type: Literal["internal", "xiaohongshu"] = "internal"


class ReportGenerateResponse(BaseModel):
    report_id: str
    status: Literal["generated", "warning", "llm_unavailable"]


class ReportRead(BaseModel):
    id: str
    prediction_id: str
    report_type: Literal["internal", "xiaohongshu"]
    content: str | None
    prompt_version: str
    llm_model: str | None
    status: Literal["generated", "warning", "llm_unavailable"]
    warnings: list[str]
    created_at: datetime
