from fastapi import APIRouter

from app.api.v1.analysis_jobs import router as analysis_jobs_router
from app.api.v1.backtests import router as backtests_router
from app.api.v1.competitions import router as competitions_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.results import router as results_router
from app.core.config import get_settings

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(competitions_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(analysis_jobs_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(ingestion_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(predictions_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(results_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(evaluation_router, prefix=get_settings().api_v1_prefix)
api_router.include_router(backtests_router, prefix=get_settings().api_v1_prefix)
