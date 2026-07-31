from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import get_redis_client


class SetupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def status(self) -> dict:
        settings = get_settings()
        checks = []
        checks.append({"name": "ADMIN_API_KEY", "status": "configured" if self._secret_configured(settings.admin_api_key) else "missing"})
        checks.append({"name": "API_FOOTBALL_KEY", "status": "configured" if self._secret_configured(settings.api_football_key) else "missing"})
        for name, value in (("LLM_BASE_URL", settings.llm_base_url), ("LLM_API_KEY", settings.llm_api_key), ("LLM_MODEL", settings.llm_model)):
            checks.append({"name": name, "status": "configured" if self._secret_configured(value) else "missing"})
        checks.append({"name": "DATABASE_URL", "status": self._database_status()})
        checks.append({"name": "REDIS_URL", "status": self._redis_status()})
        checks.append({"name": "POSTER_OUTPUT_DIR", "status": self._path_status(settings.poster_output_dir)})
        checks.append({"name": "FOOTBALL_DATA_MODE", "status": "configured" if settings.football_data_mode in {"api_football", "hybrid", "manual", "offline"} else "invalid"})
        return {"checks": checks, "data_mode": settings.football_data_mode}

    @staticmethod
    def _secret_configured(value: object) -> bool:
        if value is None:
            return False
        if hasattr(value, "get_secret_value"):
            return bool(value.get_secret_value())
        return bool(str(value).strip())

    def _database_status(self) -> str:
        try:
            self.session.execute(text("SELECT 1"))
            return "configured"
        except Exception:
            return "unreachable"

    @staticmethod
    def _redis_status() -> str:
        try:
            get_redis_client().ping()
            return "configured"
        except Exception:
            return "unreachable"

    @staticmethod
    def _path_status(path: str) -> str:
        try:
            target = Path(path)
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".write-check"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return "configured"
        except OSError:
            return "unreachable"
