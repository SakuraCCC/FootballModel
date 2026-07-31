from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import ProductionSecurityMiddleware


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Phase 1 service foundation. No prediction models are implemented.",
    )
    origins = [item.strip() for item in settings.cors_allowed_origins.split(",") if item.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Admin-API-Key"],
    )
    application.add_middleware(
        ProductionSecurityMiddleware,
        rate_limit_requests=settings.rate_limit_requests,
        rate_limit_window_seconds=settings.rate_limit_window_seconds,
    )
    application.include_router(api_router)
    output_root = Path(settings.poster_output_dir).parent
    application.mount("/generated", StaticFiles(directory=str(output_root), check_dir=False), name="generated")
    return application


app = create_app()
