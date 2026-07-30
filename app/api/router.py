from fastapi import APIRouter

from app.api.v1.competitions import router as competitions_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(competitions_router, prefix=get_settings().api_v1_prefix)
