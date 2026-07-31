"""Provider adapters and ingestion orchestration."""

from app.services.ingestion.api_football import ApiFootballProvider
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.ingestion.service import IngestionService

__all__ = ["ApiFootballProvider", "BaseProvider", "IngestionService", "ProviderResponse"]
