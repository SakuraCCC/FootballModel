from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import ModelRun, PredictionResult
from app.schemas.prediction import PredictionRead, PredictionRunRequest, PredictionRunResponse
from app.services.archive import PredictionArchiveService
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
    return PredictionRunResponse(prediction_id=result.id, status=result.status, model_version=result.model_version, feature_version=result.feature_version, data_version=result.data_version)


@router.get("/{prediction_id}", response_model=PredictionRead)
def get_prediction(
    prediction_id: str, session: Session = Depends(get_db_session)
) -> PredictionRead:
    prediction = session.get(PredictionResult, prediction_id)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prediction was not found."
        )
    model_run = session.get(ModelRun, prediction.model_run_id)
    if model_run is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Prediction model output is unavailable."
        )
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
        model_version=prediction.model_version,
        feature_version=prediction.feature_version,
        data_version=prediction.data_version,
        prompt_version=prediction.prompt_version,
        poster_version=prediction.poster_version,
    )


@router.post("/{prediction_id}/archive")
def archive_prediction(prediction_id: str, session: Session = Depends(get_db_session)) -> dict:
    try:
        archive = PredictionArchiveService(session).archive(prediction_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return {
        "archive_id": archive.id,
        "prediction_id": archive.prediction_id,
        "archived_at": archive.archived_at,
    }


@router.get("/{prediction_id}/archive")
def get_prediction_archive(prediction_id: str, session: Session = Depends(get_db_session)) -> dict:
    from app.models import PredictionArchive

    archive = (
        session.query(PredictionArchive)
        .filter(PredictionArchive.prediction_id == prediction_id)
        .one_or_none()
    )
    if archive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prediction archive was not found."
        )
    return {
        "id": archive.id,
        "prediction_id": archive.prediction_id,
        "input_summary": archive.input_summary,
        "model_output": archive.model_output,
        "report_content": archive.report_content,
        "poster_path": archive.poster_path,
        "actual_result": archive.actual_result,
        "archived_at": archive.archived_at,
        "model_version": archive.model_version,
        "feature_version": archive.feature_version,
        "data_version": archive.data_version,
        "prompt_version": archive.prompt_version,
        "poster_version": archive.poster_version,
    }
