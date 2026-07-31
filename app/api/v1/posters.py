from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import PosterOutput
from app.schemas.poster import PosterGenerateRequest, PosterGenerateResponse, PosterRead
from app.schemas.report import ReportReviewRequest
from app.services.posters import PosterService

router = APIRouter(prefix="/posters", tags=["posters"])


@router.post("/generate", response_model=PosterGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_poster(
    payload: PosterGenerateRequest, session: Session = Depends(get_db_session)
) -> PosterGenerateResponse:
    try:
        result = PosterService(session).generate(payload.report_id)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return PosterGenerateResponse(poster_id=Path(result.file_path).stem, poster_version=result.poster_version)


@router.get("/{poster_id}", response_model=PosterRead)
def get_poster(poster_id: str, session: Session = Depends(get_db_session)) -> PosterRead:
    poster = session.get(PosterOutput, poster_id)
    if poster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poster was not found")
    rendered = PosterService(session).get(poster_id)
    return PosterRead(
        id=poster.id,
        report_id=poster.report_id,
        prediction_id=poster.prediction_id,
        competition_style=poster.competition_style,
        image_url=rendered.image_url,
        template_version=poster.template_version,
        created_at=poster.created_at,
        review_status=poster.review_status,
        reviewed_at=poster.reviewed_at,
        review_notes=poster.review_notes,
        model_version=poster.model_version,
        feature_version=poster.feature_version,
        data_version=poster.data_version,
        prompt_version=poster.prompt_version,
        poster_version=poster.poster_version,
    )


@router.post("/{poster_id}/approve", response_model=PosterRead)
def approve_poster(poster_id: str, payload: ReportReviewRequest, session: Session = Depends(get_db_session)) -> PosterRead:
    try:
        poster = PosterService(session).review(poster_id, "approved", payload.notes)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    rendered = PosterService(session).get(poster.id)
    return PosterRead(id=poster.id, report_id=poster.report_id, prediction_id=poster.prediction_id, competition_style=poster.competition_style, image_url=rendered.image_url, template_version=poster.template_version, created_at=poster.created_at, review_status=poster.review_status, reviewed_at=poster.reviewed_at, review_notes=poster.review_notes, model_version=poster.model_version, feature_version=poster.feature_version, data_version=poster.data_version, prompt_version=poster.prompt_version, poster_version=poster.poster_version)


@router.post("/{poster_id}/reject", response_model=PosterRead)
def reject_poster(poster_id: str, payload: ReportReviewRequest, session: Session = Depends(get_db_session)) -> PosterRead:
    try:
        poster = PosterService(session).review(poster_id, "rejected", payload.notes)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    rendered = PosterService(session).get(poster.id)
    return PosterRead(id=poster.id, report_id=poster.report_id, prediction_id=poster.prediction_id, competition_style=poster.competition_style, image_url=rendered.image_url, template_version=poster.template_version, created_at=poster.created_at, review_status=poster.review_status, reviewed_at=poster.reviewed_at, review_notes=poster.review_notes, model_version=poster.model_version, feature_version=poster.feature_version, data_version=poster.data_version, prompt_version=poster.prompt_version, poster_version=poster.poster_version)
