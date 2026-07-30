from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Phase 1 service foundation. No prediction models are implemented.",
    )
    application.include_router(api_router)
    output_root = Path(settings.poster_output_dir).parent
    application.mount("/generated", StaticFiles(directory=str(output_root), check_dir=False), name="generated")
    return application


app = create_app()
