from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.ingestion.base import BaseProvider, ProviderResponse


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderResponseError(RuntimeError):
    pass


class ApiFootballProvider(BaseProvider):
    provider_name = "API-Football"
    api_version = "v3"
    source_tier = "secondary"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        if resolved_settings.api_football_key is None:
            raise ProviderConfigurationError("API_FOOTBALL_KEY is not configured")
        self._base_url = resolved_settings.api_football_base_url.rstrip("/")
        self._api_key = resolved_settings.api_football_key.get_secret_value()
        self._client = client or httpx.Client(timeout=20.0)

    def _get(self, endpoint: str, params: dict[str, object]) -> ProviderResponse:
        request_time = datetime.now(UTC)
        response = self._client.get(
            f"{self._base_url}/{endpoint}",
            params={key: value for key, value in params.items() if value is not None},
            headers={"x-apisports-key": self._api_key},
        )
        retrieved_at = datetime.now(UTC)
        try:
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderResponseError(f"API-Football {endpoint} request failed") from error
        if payload.get("errors"):
            raise ProviderResponseError(f"API-Football {endpoint} returned provider errors")
        data = payload.get("response")
        if not isinstance(data, list):
            raise ProviderResponseError(f"API-Football {endpoint} response is malformed")
        return ProviderResponse(
            provider=self.provider_name,
            endpoint=endpoint,
            request_time=request_time,
            retrieved_at=retrieved_at,
            response_json=payload,
            data=data,
        )

    def get_competitions(self, *, season: int | None = None) -> ProviderResponse:
        return self._get("leagues", {"season": season})

    def get_matches(
        self, *, league_id: int, season: int, match_date: str | None = None
    ) -> ProviderResponse:
        return self._get("fixtures", {"league": league_id, "season": season, "date": match_date})

    def get_team(self, *, team_id: int) -> ProviderResponse:
        return self._get("teams", {"id": team_id})

    def get_players(self, *, team_id: int, season: int | None = None) -> ProviderResponse:
        return self._get("players", {"team": team_id, "season": season})

    def get_lineups(self, *, fixture_id: int) -> ProviderResponse:
        return self._get("fixtures/lineups", {"fixture": fixture_id})

    def get_injuries(
        self, *, league_id: int, season: int, fixture_id: int | None = None
    ) -> ProviderResponse:
        return self._get(
            "injuries", {"league": league_id, "season": season, "fixture": fixture_id}
        )

    def get_statistics(self, *, fixture_id: int, team_id: int | None = None) -> ProviderResponse:
        return self._get("fixtures/statistics", {"fixture": fixture_id, "team": team_id})
