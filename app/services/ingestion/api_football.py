import time
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
        self._timeout = resolved_settings.provider_timeout_seconds
        self._max_retries = resolved_settings.provider_max_retries
        self._backoff = resolved_settings.provider_retry_backoff_seconds
        self._client = client or httpx.Client(timeout=self._timeout)

    def _get(self, endpoint: str, params: dict[str, object]) -> ProviderResponse:
        request_time = datetime.now(UTC)
        request_params = {key: value for key, value in params.items() if value is not None}
        response = None
        attempts = 0
        for attempt in range(self._max_retries + 1):
            attempts += 1
            try:
                response = self._client.get(
                    f"{self._base_url}/{endpoint}",
                    params=request_params,
                    headers={"x-apisports-key": self._api_key},
                )
            except httpx.TransportError as error:
                if attempt >= self._max_retries:
                    raise ProviderResponseError(f"API-Football {endpoint} transport failed") from error
                time.sleep(self._backoff * (2**attempt))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise ProviderResponseError(f"API-Football {endpoint} unavailable after retries")
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else self._backoff * (2**attempt)
                except ValueError:
                    delay = self._backoff * (2**attempt)
                time.sleep(min(delay, 30.0))
                continue
            break
        if response is None:
            raise ProviderResponseError(f"API-Football {endpoint} returned no response")
        retrieved_at = datetime.now(UTC)
        try:
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderResponseError(f"API-Football {endpoint} request failed") from error
        if payload.get("errors"):
            raise ProviderResponseError(f"API-Football {endpoint} returned provider errors")
        data = payload.get("response")
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ProviderResponseError(f"API-Football {endpoint} response is malformed")
        quota = {
            "x-ratelimit-requests-limit": response.headers.get("x-ratelimit-requests-limit"),
            "x-ratelimit-requests-remaining": response.headers.get("x-ratelimit-requests-remaining"),
            "x-ratelimit-requests-limit-minute": response.headers.get("x-ratelimit-requests-limit-minute"),
            "x-ratelimit-requests-remaining-minute": response.headers.get("x-ratelimit-requests-remaining-minute"),
        }
        # API gateways use multiple casing conventions; httpx.Headers lookup is case-insensitive.
        for key, aliases in {
            "daily_limit": ("X-RateLimit-Limit", "x-ratelimit-requests-limit"),
            "daily_remaining": ("X-RateLimit-Remaining", "x-ratelimit-requests-remaining"),
            "minute_limit": ("X-RateLimit-Limit-Minute", "x-ratelimit-requests-limit-minute"),
            "minute_remaining": ("X-RateLimit-Remaining-Minute", "x-ratelimit-requests-remaining-minute"),
        }.items():
            if quota.get(aliases[-1]) is None:
                for alias in aliases:
                    value = response.headers.get(alias)
                    if value is not None:
                        quota[aliases[-1]] = value
                        break
        return ProviderResponse(
            provider=self.provider_name,
            endpoint=endpoint,
            request_time=request_time,
            retrieved_at=retrieved_at,
            response_json=payload,
            data=data,
            quota={key: value for key, value in quota.items() if value is not None},
            status_code=response.status_code,
            request_attempts=attempts,
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

    def get_standings(self, *, league_id: int, season: int) -> ProviderResponse:
        return self._get("standings", {"league": league_id, "season": season})

    def get_status(self) -> ProviderResponse:
        return self._get("status", {})
