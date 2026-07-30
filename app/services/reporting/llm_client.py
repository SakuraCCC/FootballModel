from typing import Protocol

import httpx

from app.core.config import Settings, get_settings
from app.services.reporting.schemas import LLMGeneration, ReportContext


class ReportLLMClient(Protocol):
    def generate(self, *, prompt: str, context: ReportContext) -> LLMGeneration: ...


class OpenAICompatibleLLMClient:
    """Small OpenAI-compatible client with a safe, non-throwing unavailable mode."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def generate(self, *, prompt: str, context: ReportContext) -> LLMGeneration:
        base_url = self._settings.llm_base_url
        api_key = self._settings.llm_api_key
        model = self._settings.llm_model
        if not base_url or api_key is None or not model:
            return LLMGeneration(status="llm_unavailable")
        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key.get_secret_value()}"},
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": context.model_dump_json()},
                    ],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                return LLMGeneration(status="llm_unavailable")
            return LLMGeneration(status="generated", content=content.strip(), model=model)
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return LLMGeneration(status="llm_unavailable")
