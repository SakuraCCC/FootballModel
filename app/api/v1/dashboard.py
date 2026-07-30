from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.dashboard import (
    ContentAssetSummaryRead,
    DashboardSummaryRead,
    ModelPerformanceDashboardRead,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryRead)
def dashboard_summary(session: Session = Depends(get_db_session)) -> DashboardSummaryRead:
    return DashboardSummaryRead(**DashboardService(session).summary())


@router.get("/model-performance", response_model=ModelPerformanceDashboardRead)
def model_performance(session: Session = Depends(get_db_session)) -> ModelPerformanceDashboardRead:
    return ModelPerformanceDashboardRead(**DashboardService(session).model_performance())


@router.get("/content-assets", response_model=ContentAssetSummaryRead)
def content_assets(
    start_date: date | None = None,
    end_date: date | None = None,
    competition_code: str | None = None,
    match_id: str | None = None,
    session: Session = Depends(get_db_session),
) -> ContentAssetSummaryRead:
    return ContentAssetSummaryRead(
        **DashboardService(session).content_assets(
            start_date=start_date,
            end_date=end_date,
            competition_code=competition_code,
            match_id=match_id,
        )
    )
