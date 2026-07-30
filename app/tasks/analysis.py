import logging
from collections.abc import Callable

from celery import chain
from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models import AnalysisJob, AnalysisResult
from app.schemas.analysis import (
    MatchAnalysisResult,
    MatchInfo,
    ModelOutputs,
    PipelineTestSection,
    ScoreReview,
)
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _load_job(session, job_id: str) -> AnalysisJob:
    job = session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.id == job_id)
        .options(selectinload(AnalysisJob.matches), selectinload(AnalysisJob.results))
    )
    if job is None:
        raise ValueError(f"Analysis job {job_id} does not exist")
    return job


def _run_step(job_id: str, step: str, action: Callable[[AnalysisJob], object]) -> object:
    session = SessionLocal()
    try:
        job = _load_job(session, job_id)
        job.status = "running"
        job.current_step = step
        job.error_message = None
        session.commit()
        logger.info("analysis_job_step_started job_id=%s step=%s", job_id, step)
        result = action(job)
        session.commit()
        logger.info("analysis_job_step_completed job_id=%s step=%s", job_id, step)
        return result
    except Exception as error:
        session.rollback()
        job = session.get(AnalysisJob, job_id)
        if job is not None:
            job.status = "failed"
            job.current_step = step
            job.error_message = str(error)[:1000]
            session.commit()
        logger.exception("analysis_job_step_failed job_id=%s step=%s", job_id, step)
        raise
    finally:
        session.close()


@celery_app.task(name="analysis.create_analysis_job")
def create_analysis_job_task(job_id: str) -> str:
    _run_step(job_id, "create_analysis_job", lambda _job: None)
    return job_id


@celery_app.task(name="analysis.validate_input")
def validate_input_task(job_id: str) -> str:
    def validate(job: AnalysisJob) -> None:
        if not job.competition_name.strip():
            raise ValueError("competition_name is required")
        if not job.matches:
            raise ValueError("at least one match is required")
        for match in job.matches:
            if not match.home_team.strip() or not match.away_team.strip():
                raise ValueError("both team names are required")
            if match.home_team.casefold() == match.away_team.casefold():
                raise ValueError("home_team and away_team must differ")

    _run_step(job_id, "validate_input", validate)
    return job_id


def _pipeline_section(name: str) -> PipelineTestSection:
    return PipelineTestSection(note=f"{name} is unavailable: pipeline test fixture only.")


@celery_app.task(name="analysis.generate_analysis_result")
def generate_analysis_result_task(job_id: str) -> dict[str, object]:
    def generate(job: AnalysisJob) -> dict[str, object]:
        results = []
        for match in job.matches:
            result = MatchAnalysisResult(
                match_info=MatchInfo(
                    competition_name=job.competition_name,
                    match_date=job.match_date,
                    home_team=match.home_team,
                    away_team=match.away_team,
                ),
                recent_form=_pipeline_section("recent_form"),
                attack_analysis=_pipeline_section("attack_analysis"),
                defense_analysis=_pipeline_section("defense_analysis"),
                fatigue_analysis=_pipeline_section("fatigue_analysis"),
                injury_analysis=_pipeline_section("injury_analysis"),
                tactical_analysis=_pipeline_section("tactical_analysis"),
                model_outputs=ModelOutputs(
                    note="No prediction model or real football data source is used in Phase 2."
                ),
                score_review=ScoreReview(
                    note="No score review is executed in the Phase 2 pipeline test."
                ),
                final_conclusion=(
                    "Pipeline test completed with a fixed placeholder structure; "
                    "this is not a real analysis or prediction."
                ),
            )
            results.append({"match_id": match.id, "structured_json": result.model_dump(mode="json")})
        return {"job_id": job.id, "results": results}

    return _run_step(job_id, "generate_analysis_result", generate)


@celery_app.task(name="analysis.save_result")
def save_result_task(payload: dict[str, object]) -> str:
    job_id = str(payload["job_id"])

    def save(job: AnalysisJob) -> str:
        for generated_result in payload["results"]:
            match_id = str(generated_result["match_id"])
            existing = next((item for item in job.results if item.match_id == match_id), None)
            if existing is None:
                job.results.append(
                    AnalysisResult(
                        match_id=match_id,
                        structured_json=generated_result["structured_json"],
                        status="completed",
                    )
                )
        job.status = "completed"
        job.current_step = "completed"
        return job.id

    return _run_step(job_id, "save_result", save)


def enqueue_analysis_pipeline(job_id: str) -> AsyncResult:
    workflow = chain(
        create_analysis_job_task.s(job_id),
        validate_input_task.s(),
        generate_analysis_result_task.s(),
        save_result_task.s(),
    )
    logger.info("analysis_job_pipeline_enqueued job_id=%s", job_id)
    return workflow.apply_async()
