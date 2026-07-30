from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse, ReportRead
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
    return ReportGenerateResponse(report_id=result.report_id, status=result.status)


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
        created_at=report.created_at,
    )
