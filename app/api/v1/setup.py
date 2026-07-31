import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.schemas.phase11 import DataModeRequest, SetupStatusRead
from app.services.setup import SetupService

router = APIRouter(prefix="/setup", tags=["setup"])
logger = logging.getLogger(__name__)


@router.get("/status", response_model=SetupStatusRead)
def setup_status(session: Session = Depends(get_db_session)) -> SetupStatusRead:
    return SetupStatusRead(**SetupService(session).status())


@router.post("/data-mode", response_model=SetupStatusRead)
def set_data_mode(payload: DataModeRequest, session: Session = Depends(get_db_session)) -> SetupStatusRead:
    settings = get_settings()
    settings.football_data_mode = payload.mode
    logger.info("data_mode_changed mode=%s", payload.mode)
    return SetupStatusRead(**SetupService(session).status())
