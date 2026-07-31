from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sakura Football Model API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://football_model:change-me-before-production@db:5432/football_model"
    redis_url: str = "redis://redis:6379/0"
    api_football_key: SecretStr | None = None
    api_football_base_url: str = "https://v3.football.api-sports.io"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    poster_output_dir: str = "generated/posters"
    temporary_file_dir: str = "generated/tmp"
    log_level: str = "INFO"
    log_format: str = "json"
    admin_api_key: SecretStr | None = None
    cors_allowed_origins: str = ""
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    provider_timeout_seconds: float = 20.0
    provider_max_retries: int = 3
    provider_retry_backoff_seconds: float = 0.5
    target_season: int = 2026

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
