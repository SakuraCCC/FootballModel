from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_api_football_provider, get_db_session
from app.schemas.ingestion import (
    CompetitionSyncRequest,
    IngestionSummaryRead,
    MatchSyncRequest,
)
from app.services.ingestion.api_football import ProviderConfigurationError, ProviderResponseError
from app.services.ingestion.service import IngestionError, IngestionService

router = APIRouter(prefix="/ingestion/api-football", tags=["ingestion"])


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, ProviderConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    if isinstance(error, (ProviderResponseError, IngestionError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Data provider request failed")


@router.post("/competitions", response_model=IngestionSummaryRead)
def sync_competitions(
    payload: CompetitionSyncRequest,
    session: Session = Depends(get_db_session),
    provider=Depends(get_api_football_provider),
) -> IngestionSummaryRead:
    try:
        return IngestionSummaryRead(
            **IngestionService(session, provider).sync_competitions(season=payload.season).__dict__
        )
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/matches", response_model=IngestionSummaryRead)
def sync_matches(
    payload: MatchSyncRequest,
    session: Session = Depends(get_db_session),
    provider=Depends(get_api_football_provider),
) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_matches(
            competition_code=payload.competition_code,
            season=payload.season,
            match_date=payload.match_date,
        )
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error
