from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import ModelRun, PredictionResult
from app.schemas.prediction import PredictionRead, PredictionRunRequest, PredictionRunResponse
from app.services.prediction.pipeline import PredictionPipeline

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/run", response_model=PredictionRunResponse, status_code=status.HTTP_201_CREATED)
def run_prediction(
    payload: PredictionRunRequest, session: Session = Depends(get_db_session)
) -> PredictionRunResponse:
    try:
        result = PredictionPipeline(session).run(payload.match_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return PredictionRunResponse(prediction_id=result.id, status=result.status)


@router.get("/{prediction_id}", response_model=PredictionRead)
def get_prediction(prediction_id: str, session: Session = Depends(get_db_session)) -> PredictionRead:
    prediction = session.get(PredictionResult, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction was not found.")
    model_run = session.get(ModelRun, prediction.model_run_id)
    if model_run is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Prediction model output is unavailable.")
    return PredictionRead(
        id=prediction.id,
        match_id=prediction.match_id,
        model_run_id=prediction.model_run_id,
        status=prediction.status,
        direction=prediction.direction,
        goal_range=prediction.goal_range,
        btts=prediction.btts,
        primary_score=prediction.primary_score,
        stable_score=prediction.stable_score,
        alternative_score=prediction.alternative_score,
        review_summary=prediction.review_summary,
        confidence=prediction.confidence,
        created_at=prediction.created_at,
        model_output=model_run.output_json,
    )
