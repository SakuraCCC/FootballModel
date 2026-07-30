from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.evaluation import BacktestRunRequest, BacktestRunResponse
from app.services.backtest import BacktestPipeline

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
def run_backtest(
    payload: BacktestRunRequest, session: Session = Depends(get_db_session)
) -> BacktestRunResponse:
    try:
        result = BacktestPipeline(session).run(
            competition_code=payload.competition_code,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return BacktestRunResponse(
        processed=result.processed,
        evaluated=result.evaluated,
        skipped_not_available=result.skipped_not_available,
        prediction_ids=result.prediction_ids,
    )
