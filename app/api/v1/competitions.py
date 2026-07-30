from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import Competition
from app.schemas.competition import CompetitionRead

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("", response_model=list[CompetitionRead])
def list_competitions(session: Session = Depends(get_db_session)) -> list[Competition]:
    """List competition metadata; no match or prediction data is exposed."""
    return list(session.scalars(select(Competition).order_by(Competition.code)))


@router.get("/{code}", response_model=CompetitionRead)
def get_competition(code: str, session: Session = Depends(get_db_session)) -> Competition:
    competition = session.scalar(select(Competition).where(Competition.code == code.upper()))
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "competition_not_found", "message": f"Competition '{code}' was not found."},
        )
    return competition
