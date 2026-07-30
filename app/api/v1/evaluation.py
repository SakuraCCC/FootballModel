from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.evaluation import EvaluationRead, EvaluationRunRequest, EvaluationSummaryRead
from app.services.evaluation import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
def run_evaluation(
    payload: EvaluationRunRequest, session: Session = Depends(get_db_session)
) -> EvaluationRead:
    try:
        result = EvaluationService(session).evaluate(payload.prediction_id, payload.actual_result_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return EvaluationRead(
        id=result.id,
        prediction_id=result.prediction_id,
        actual_result_id=result.actual_result_id,
        direction_correct=result.direction_correct,
        score_exact_correct=result.score_exact_correct,
        score_top3_correct=result.score_top3_correct,
        goal_range_correct=result.goal_range_correct,
        btts_correct=result.btts_correct,
        log_loss=result.log_loss,
        brier_score=result.brier_score,
        evaluated_at=result.evaluated_at,
    )


@router.get("/summary", response_model=EvaluationSummaryRead)
def evaluation_summary(session: Session = Depends(get_db_session)) -> EvaluationSummaryRead:
    return EvaluationSummaryRead(**EvaluationService(session).summary())


@router.get("/competition/{competition_code}", response_model=EvaluationSummaryRead)
def competition_summary(
    competition_code: str, session: Session = Depends(get_db_session)
) -> EvaluationSummaryRead:
    try:
        return EvaluationSummaryRead(**EvaluationService(session).summary(competition_code))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
