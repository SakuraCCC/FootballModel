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

    competition: Mapped[Competition] = relationship(back_populates="seasons")
    matches: Mapped[list["Match"]] = relationship(back_populates="season")


class Team(TimestampedModel, Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("canonical_name", "country_code", name="uq_teams_name_country"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)


class Match(TimestampedModel, Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id <> away_team_id", name="ck_matches_distinct_teams"),
        Index("ix_matches_competition_kickoff", "competition_id", "kickoff_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    competition_id: Mapped[str] = mapped_column(ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[str | None] = mapped_column(ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=True)
    home_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    away_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="scheduled", nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="matches")
    season: Mapped[Season | None] = relationship(back_populates="matches")


class DataSource(TimestampedModel, Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reliability_level: Mapped[str] = mapped_column(String(24), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


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
