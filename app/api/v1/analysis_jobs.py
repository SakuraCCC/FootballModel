from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_analysis_job_dispatcher, get_db_session
from app.schemas.analysis import AnalysisJobCreate, AnalysisJobRead, AnalysisJobResultRead
from app.services.analysis_jobs import (
    PipelineDispatcher,
    create_analysis_job,
    get_analysis_job_or_none,
    serialize_job,
    serialize_results,
)

router = APIRouter(prefix="/analysis-jobs", tags=["analysis-jobs"])


@router.post("", response_model=AnalysisJobRead, status_code=status.HTTP_201_CREATED)
def post_analysis_job(
    payload: AnalysisJobCreate,
    session: Session = Depends(get_db_session),
    dispatcher: PipelineDispatcher = Depends(get_analysis_job_dispatcher),
) -> AnalysisJobRead:
    job = create_analysis_job(session, payload)
    try:
        dispatcher(job.id)
    except Exception:
        job.status = "failed"
        job.current_step = "enqueue_analysis_pipeline"
        job.error_message = "Unable to enqueue analysis job."
        session.commit()
    return serialize_job(get_analysis_job_or_none(session, job.id) or job)


@router.get("/{job_id}", response_model=AnalysisJobRead)
def get_analysis_job(job_id: str, session: Session = Depends(get_db_session)) -> AnalysisJobRead:
    job = get_analysis_job_or_none(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job was not found.")
    return serialize_job(job)


@router.get("/{job_id}/result", response_model=AnalysisJobResultRead)
def get_analysis_job_result(job_id: str, session: Session = Depends(get_db_session)) -> AnalysisJobResultRead:
    job = get_analysis_job_or_none(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job was not found.")
    if not job.results:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis result is not available until the pipeline completes.",
        )
    return serialize_results(job)
