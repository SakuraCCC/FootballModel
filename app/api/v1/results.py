from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.evaluation import ActualResultCreate, ActualResultRead
from app.services.results import ResultService

router = APIRouter(prefix="/results", tags=["results"])


@router.post("", response_model=ActualResultRead, status_code=status.HTTP_201_CREATED)
def create_actual_result(
    payload: ActualResultCreate, session: Session = Depends(get_db_session)
) -> ActualResultRead:
    try:
        result = ResultService(session).record(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return ActualResultRead(
        id=result.id,
        match_id=result.match_id,
        home_score=result.home_score,
        away_score=result.away_score,
        result=result.result,
        total_goals=result.total_goals,
        btts_result=result.btts_result,
        completed_at=result.completed_at,
    )
