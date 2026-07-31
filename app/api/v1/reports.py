from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.report import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportRead,
    ReportReviewRequest,
)
from app.services.reporting import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerateRequest, session: Session = Depends(get_db_session)
) -> ReportGenerateResponse:
    try:
        result = ReportService(session).generate(payload.prediction_id, payload.report_type)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return ReportGenerateResponse(report_id=result.report_id, status=result.status, prompt_version=result.prompt_version, model_version=result.model_version)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: str, session: Session = Depends(get_db_session)) -> ReportRead:
    try:
        report = ReportService(session).get(report_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return ReportRead(
        id=report.report_id,
        prediction_id=report.prediction_id,
        report_type=report.report_type,
        content=report.content,
        prompt_version=report.prompt_version,
        llm_model=report.llm_model,
        status=report.status,
        warnings=report.warnings,
        review_status=report.review_status,
        reviewed_at=report.reviewed_at,
        review_notes=report.review_notes,
        created_at=report.created_at,
        model_version=report.model_version,
        feature_version=report.feature_version,
        data_version=report.data_version,
        poster_version=report.poster_version,
    )


@router.post("/{report_id}/approve", response_model=ReportRead)
def approve_report(report_id: str, payload: ReportReviewRequest, session: Session = Depends(get_db_session)) -> ReportRead:
    try:
        report = ReportService(session).review(report_id, "approved", payload.notes)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _read(report)


@router.post("/{report_id}/reject", response_model=ReportRead)
def reject_report(report_id: str, payload: ReportReviewRequest, session: Session = Depends(get_db_session)) -> ReportRead:
    try:
        report = ReportService(session).review(report_id, "rejected", payload.notes)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _read(report)


def _read(report) -> ReportRead:
    return ReportRead(id=report.report_id, prediction_id=report.prediction_id, report_type=report.report_type, content=report.content, prompt_version=report.prompt_version, llm_model=report.llm_model, status=report.status, warnings=report.warnings, review_status=report.review_status, reviewed_at=report.reviewed_at, review_notes=report.review_notes, created_at=report.created_at, model_version=report.model_version, feature_version=report.feature_version, data_version=report.data_version, poster_version=report.poster_version)
