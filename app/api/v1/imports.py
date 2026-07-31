from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.phase11 import ManualImportRequest
from app.services.manual_import import ManualImportError, ManualImportService

router = APIRouter(prefix="/import", tags=["manual-import"])


def _run(kind: str, payload: ManualImportRequest, session: Session) -> dict:
    data = payload.model_dump(exclude_none=True)
    try:
        return ManualImportService(session).import_records(kind, data)
    except ManualImportError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/matches")
def import_matches(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("matches", payload, session)


@router.post("/results")
def import_results(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("results", payload, session)


@router.post("/standings")
def import_standings(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("standings", payload, session)


@router.post("/injuries")
def import_injuries(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("injuries", payload, session)


@router.post("/lineups")
def import_lineups(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("lineups", payload, session)


@router.post("/statistics")
def import_statistics(payload: ManualImportRequest, session: Session = Depends(get_db_session)) -> dict:
    return _run("statistics", payload, session)
