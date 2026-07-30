from collections.abc import Callable

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AnalysisJob, AnalysisJobMatch
from app.schemas.analysis import (
    AnalysisJobCreate,
    AnalysisJobRead,
    AnalysisJobResultRead,
    AnalysisResultRead,
)

PipelineDispatcher = Callable[[str], AsyncResult]


def create_analysis_job(session: Session, payload: AnalysisJobCreate) -> AnalysisJob:
    job = AnalysisJob(
        competition_name=payload.competition_name.strip(),
        match_date=payload.match_date,
        model_version=payload.model_version.strip(),
        poster_style=payload.poster_style.strip(),
        watermark=payload.watermark.strip(),
        matches=[
            AnalysisJobMatch(home_team=match.home_team.strip(), away_team=match.away_team.strip())
            for match in payload.matches
        ],
    )
    session.add(job)
    session.commit()
    return get_analysis_job_or_none(session, job.id) or job


def get_analysis_job_or_none(session: Session, job_id: str) -> AnalysisJob | None:
    statement = (
        select(AnalysisJob)
        .where(AnalysisJob.id == job_id)
        .options(selectinload(AnalysisJob.matches), selectinload(AnalysisJob.results))
    )
    return session.scalar(statement)


def serialize_job(job: AnalysisJob) -> AnalysisJobRead:
    return AnalysisJobRead(
        id=job.id,
        batch_id=job.batch_id,
        competition_name=job.competition_name,
        match_date=job.match_date,
        model_version=job.model_version,
        poster_style=job.poster_style,
        watermark=job.watermark,
        status=job.status,
        current_step=job.current_step,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        is_completed=job.status == "completed",
        matches=[
            {"id": match.id, "home_team": match.home_team, "away_team": match.away_team}
            for match in job.matches
        ],
    )


def serialize_results(job: AnalysisJob) -> AnalysisJobResultRead:
    return AnalysisJobResultRead(
        job_id=job.id,
        status=job.status,
        is_completed=job.status == "completed",
        results=[
            AnalysisResultRead(
                id=result.id,
                match_id=result.match_id,
                status=result.status,
                structured_json=result.structured_json,
                created_at=result.created_at,
                updated_at=result.updated_at,
            )
            for result in sorted(job.results, key=lambda item: item.created_at)
        ],
    )
