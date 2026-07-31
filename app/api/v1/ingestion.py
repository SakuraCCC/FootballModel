from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_api_football_provider, get_db_session
from app.schemas.ingestion import (
    CompetitionSyncRequest,
    IngestionSummaryRead,
    InjurySyncRequest,
    LineupSyncRequest,
    MatchSyncRequest,
    PlayerSyncRequest,
    ResultsSyncRequest,
    StandingsSyncRequest,
    StatisticsSyncRequest,
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


@router.post("/standings", response_model=IngestionSummaryRead)
def sync_standings(payload: StandingsSyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_standings(competition_code=payload.competition_code, season=payload.season)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/players", response_model=IngestionSummaryRead)
def sync_players(payload: PlayerSyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_players(team_id=payload.team_id, season=payload.season, competition_code=payload.competition_code)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/injuries", response_model=IngestionSummaryRead)
def sync_injuries(payload: InjurySyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_injuries(competition_code=payload.competition_code, season=payload.season, fixture_id=payload.fixture_id)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/lineups", response_model=IngestionSummaryRead)
def sync_lineups(payload: LineupSyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_lineups(match_id=payload.match_id, fixture_id=payload.fixture_id)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/statistics", response_model=IngestionSummaryRead)
def sync_statistics(payload: StatisticsSyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_statistics(match_id=payload.match_id, fixture_id=payload.fixture_id)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error


@router.post("/results", response_model=IngestionSummaryRead)
def sync_results(payload: ResultsSyncRequest, session: Session = Depends(get_db_session), provider=Depends(get_api_football_provider)) -> IngestionSummaryRead:
    try:
        summary = IngestionService(session, provider).sync_results(competition_code=payload.competition_code, season=payload.season, match_date=payload.match_date)
        return IngestionSummaryRead(**summary.__dict__)
    except Exception as error:
        raise _to_http_error(error) from error
