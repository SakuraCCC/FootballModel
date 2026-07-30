from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ReportType = Literal["internal", "xiaohongshu"]


class SourceReference(BaseModel):
    snapshot_id: str
    provider: str
    endpoint: str
    retrieved_at: datetime


class ReportFact(BaseModel):
    label: str
    value: str
    certainty: Literal["official", "confirmed", "reported", "predicted", "unavailable"]
    source_snapshot_ids: list[str] = Field(default_factory=list)


class ReportContext(BaseModel):
    prediction_id: str
    match_info: dict[str, Any]
    confirmed_facts: list[ReportFact]
    reported_information: list[ReportFact]
    model_prediction: dict[str, Any]
    score_review: dict[str, Any]
    risk_warning: list[str]
    data_completeness: str
    confidence: str
    source_snapshots: list[SourceReference]
    evaluation_results: dict[str, Any] | None


class LLMGeneration(BaseModel):
    status: Literal["generated", "llm_unavailable"]
    content: str | None = None
    model: str | None = None


class FactCheckResult(BaseModel):
    status: Literal["passed", "warning"]
    warnings: list[str] = Field(default_factory=list)


class ContentGuardResult(BaseModel):
    status: Literal["passed", "warning"]
    warnings: list[str] = Field(default_factory=list)


class GeneratedReport(BaseModel):
    report_id: str
    prediction_id: str
    report_type: ReportType
    content: str | None
    prompt_version: str
    llm_model: str | None
    status: Literal["generated", "warning", "llm_unavailable"]
    warnings: list[str]
    created_at: datetime
