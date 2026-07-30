from datetime import UTC

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.ingestion.api_football import ApiFootballProvider, ProviderConfigurationError


def test_api_football_adapter_uses_key_header_and_unwraps_response() -> None:
    received_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal received_request
        received_request = request
        return httpx.Response(
            200,
            json={"response": [{"league": {"id": 169, "name": "Super League"}}], "errors": {}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ApiFootballProvider(
        settings=Settings(
            api_football_key=SecretStr("test-key"),
            api_football_base_url="https://example.test",
        ),
        client=client,
    )

    result = provider.get_competitions(season=2026)

    assert received_request is not None
    assert received_request.headers["x-apisports-key"] == "test-key"
    assert received_request.url.path == "/leagues"
    assert result.provider == "API-Football"
    assert result.endpoint == "leagues"
    assert result.data[0]["league"]["id"] == 169
    assert result.request_time.tzinfo == UTC


def test_api_football_adapter_requires_environment_key() -> None:
    with pytest.raises(ProviderConfigurationError, match="API_FOOTBALL_KEY"):
        ApiFootballProvider(settings=Settings(api_football_key=None))
