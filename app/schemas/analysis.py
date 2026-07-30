from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisJobMatchCreate(BaseModel):
    home_team: str = Field(min_length=1, max_length=160)
    away_team: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def teams_must_differ(self) -> "AnalysisJobMatchCreate":
        if self.home_team.strip().casefold() == self.away_team.strip().casefold():
            raise ValueError("home_team and away_team must differ")
        return self


class AnalysisJobCreate(BaseModel):
    competition_name: str = Field(min_length=1, max_length=160)
    match_date: date
    matches: list[AnalysisJobMatchCreate] = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=120)
    poster_style: str = Field(min_length=1, max_length=80)
    watermark: str = Field(min_length=1, max_length=160)


class AnalysisJobMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    home_team: str
    away_team: str


class AnalysisJobRead(BaseModel):
    id: str
    batch_id: str
    competition_name: str
    match_date: date
    model_version: str
    poster_style: str
    watermark: str
    status: str
    current_step: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    is_completed: bool
    matches: list[AnalysisJobMatchRead]


class PipelineTestSection(BaseModel):
    status: Literal["not_available"] = "not_available"
    note: str


class MatchInfo(BaseModel):
    competition_name: str
    match_date: date
    home_team: str
    away_team: str


class ModelOutputs(BaseModel):
    status: Literal["not_executed"] = "not_executed"
    note: str
    predictions: list[object] = Field(default_factory=list)


class ScoreReview(BaseModel):
    status: Literal["not_executed"] = "not_executed"
    note: str
    candidate_scores: list[object] = Field(default_factory=list)


class MatchAnalysisResult(BaseModel):
    mock_for_pipeline_test: Literal[True] = True
    match_info: MatchInfo
    recent_form: PipelineTestSection
    attack_analysis: PipelineTestSection
    defense_analysis: PipelineTestSection
    fatigue_analysis: PipelineTestSection
    injury_analysis: PipelineTestSection
    tactical_analysis: PipelineTestSection
    model_outputs: ModelOutputs
    score_review: ScoreReview
    final_conclusion: str


class AnalysisResultRead(BaseModel):
    id: str
    match_id: str
    status: str
    structured_json: MatchAnalysisResult
    created_at: datetime
    updated_at: datetime


class AnalysisJobResultRead(BaseModel):
    job_id: str
    status: str
    is_completed: bool
    results: list[AnalysisResultRead]
