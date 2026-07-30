from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import PosterOutput
from app.schemas.poster import PosterGenerateRequest, PosterGenerateResponse, PosterRead
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
    return PosterGenerateResponse(poster_id=Path(result.file_path).stem)


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
    )
