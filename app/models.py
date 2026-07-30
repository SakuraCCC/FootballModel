from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uuid_string() -> str:
    return str(uuid4())


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Competition(TimestampedModel, Base):
    __tablename__ = "competitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    api_football_league_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    certainty: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable")

    seasons: Mapped[list["Season"]] = relationship(back_populates="competition")
    matches: Mapped[list["Match"]] = relationship(back_populates="competition")


class Season(TimestampedModel, Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("competition_id", "code", name="uq_seasons_competition_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    competition_id: Mapped[str] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True)
    certainty: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable")

    competition: Mapped[Competition] = relationship(back_populates="seasons")
    matches: Mapped[list["Match"]] = relationship(back_populates="season")


class Team(TimestampedModel, Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("canonical_name", "country_code", name="uq_teams_name_country"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    normalized_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True)
    certainty: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable")


class Match(TimestampedModel, Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id <> away_team_id", name="ck_matches_distinct_teams"),
        Index("ix_matches_competition_kickoff", "competition_id", "kickoff_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    competition_id: Mapped[str] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[str | None] = mapped_column(ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=True)
    home_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True)
    away_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True)
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="scheduled", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True)
    certainty: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable")

    competition: Mapped[Competition] = relationship(back_populates="matches")
    season: Mapped[Season | None] = relationship(back_populates="matches")


class DataSource(TimestampedModel, Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="secondary")
    api_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reliability_level: Mapped[str] = mapped_column(String(24), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


class RawDataSnapshot(TimestampedModel, Base):
    __tablename__ = "raw_data_snapshots"
    __table_args__ = (Index("ix_raw_data_snapshots_source_retrieved", "data_source_id", "retrieved_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    data_source_id: Mapped[str] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    request_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Player(TimestampedModel, Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True)
    certainty: Mapped[str] = mapped_column(String(24), nullable=False, default="unavailable")


class ModelVersion(TimestampedModel, Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_versions_name_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class ModelRun(TimestampedModel, Base):
    __tablename__ = "model_runs"
    __table_args__ = (Index("ix_model_runs_match_created", "match_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False)
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    input_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("raw_data_snapshots.id", ondelete="RESTRICT"), nullable=True
    )
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[str] = mapped_column(String(24), nullable=False)
    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="SET NULL", use_alter=True), nullable=True
    )


class PredictionResult(TimestampedModel, Base):
    __tablename__ = "prediction_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False)
    model_run_id: Mapped[str] = mapped_column(ForeignKey("model_runs.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    btts: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_score: Mapped[str | None] = mapped_column(String(16), nullable=True)
    stable_score: Mapped[str | None] = mapped_column(String(16), nullable=True)
    alternative_score: Mapped[str | None] = mapped_column(String(16), nullable=True)
    review_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[str] = mapped_column(String(24), nullable=False)


class Prediction(TimestampedModel, Base):
    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_match_created", "match_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    data_snapshot_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    output_version: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class ActualResult(TimestampedModel, Base):
    __tablename__ = "actual_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="RESTRICT"), unique=True, nullable=False)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    result_source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    total_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    btts_result: Mapped[bool | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalysisJob(TimestampedModel, Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (Index("ix_analysis_jobs_batch_id", "batch_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, default=uuid_string)
    competition_name: Mapped[str] = mapped_column(String(160), nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    poster_style: Mapped[str] = mapped_column(String(80), nullable=False)
    watermark: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    matches: Mapped[list["AnalysisJobMatch"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class AnalysisJobMatch(TimestampedModel, Base):
    __tablename__ = "analysis_job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "home_team", "away_team", name="uq_analysis_job_matches_teams"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False
    )
    home_team: Mapped[str] = mapped_column(String(160), nullable=False)
    away_team: Mapped[str] = mapped_column(String(160), nullable=False)

    job: Mapped[AnalysisJob] = relationship(back_populates="matches")
    results: Mapped[list["AnalysisResult"]] = relationship(back_populates="match")


class AnalysisResult(TimestampedModel, Base):
    __tablename__ = "analysis_results"
    __table_args__ = (UniqueConstraint("job_id", "match_id", name="uq_analysis_results_job_match"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_job_matches.id", ondelete="CASCADE"), nullable=False
    )
    structured_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="completed")

    job: Mapped[AnalysisJob] = relationship(back_populates="results")
    match: Mapped[AnalysisJobMatch] = relationship(back_populates="results")


class PredictionEvaluation(TimestampedModel, Base):
    __tablename__ = "prediction_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    actual_result_id: Mapped[str] = mapped_column(
        ForeignKey("actual_results.id", ondelete="RESTRICT"), nullable=False
    )
    direction_correct: Mapped[bool] = mapped_column(nullable=False)
    score_exact_correct: Mapped[bool] = mapped_column(nullable=False)
    score_top3_correct: Mapped[bool] = mapped_column(nullable=False)
    goal_range_correct: Mapped[bool] = mapped_column(nullable=False)
    btts_correct: Mapped[bool] = mapped_column(nullable=False)
    log_loss: Mapped[float | None] = mapped_column(nullable=True)
    brier_score: Mapped[float | None] = mapped_column(nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelPerformance(TimestampedModel, Base):
    __tablename__ = "model_performance"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "competition_id",
            name="uq_model_performance_version_competition",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(nullable=True)
    log_loss: Mapped[float | None] = mapped_column(nullable=True)
    brier_score: Mapped[float | None] = mapped_column(nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportOutput(TimestampedModel, Base):
    __tablename__ = "report_outputs"
    __table_args__ = (Index("ix_report_outputs_prediction_created", "prediction_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="RESTRICT"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class PosterOutput(TimestampedModel, Base):
    __tablename__ = "poster_outputs"
    __table_args__ = (Index("ix_poster_outputs_report_created", "report_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    report_id: Mapped[str] = mapped_column(ForeignKey("report_outputs.id", ondelete="RESTRICT"), nullable=False)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="RESTRICT"), nullable=False
    )
    competition_style: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    template_version: Mapped[str] = mapped_column(String(80), nullable=False)


class ContentPublishRecord(TimestampedModel, Base):
    __tablename__ = "content_publish_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    report_id: Mapped[str] = mapped_column(ForeignKey("report_outputs.id", ondelete="RESTRICT"), nullable=False)
    poster_id: Mapped[str | None] = mapped_column(
        ForeignKey("poster_outputs.id", ondelete="RESTRICT"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    collects: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AutomationRun(TimestampedModel, Base):
    __tablename__ = "automation_runs"
    __table_args__ = (Index("ix_automation_runs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id", ondelete="RESTRICT"), unique=True, nullable=False)
    analysis_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"), nullable=True
    )
    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="SET NULL"), nullable=True
    )
    report_id: Mapped[str | None] = mapped_column(
        ForeignKey("report_outputs.id", ondelete="SET NULL"), nullable=True
    )
    poster_id: Mapped[str | None] = mapped_column(
        ForeignKey("poster_outputs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="discovered")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
