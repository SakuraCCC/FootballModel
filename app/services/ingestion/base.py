from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    endpoint: str
    request_time: datetime
    retrieved_at: datetime
    response_json: dict[str, Any]
    data: list[dict[str, Any]]
    quota: dict[str, Any] | None = None
    status_code: int | None = None
    snapshot_id: str | None = None
    cached: bool = False
    request_attempts: int = 1


class BaseProvider(ABC):
    """All third-party football data access must pass through this contract."""

    provider_name: str
    api_version: str
    source_tier: str

    @abstractmethod
    def get_competitions(self, *, season: int | None = None) -> ProviderResponse: ...

    @abstractmethod
    def get_matches(
        self, *, league_id: int, season: int, match_date: str | None = None
    ) -> ProviderResponse: ...

    @abstractmethod
    def get_team(self, *, team_id: int) -> ProviderResponse: ...

    @abstractmethod
    def get_players(self, *, team_id: int, season: int | None = None) -> ProviderResponse: ...

    @abstractmethod
    def get_lineups(self, *, fixture_id: int) -> ProviderResponse: ...

    @abstractmethod
    def get_injuries(
        self, *, league_id: int, season: int, fixture_id: int | None = None
    ) -> ProviderResponse: ...

    @abstractmethod
    def get_statistics(self, *, fixture_id: int, team_id: int | None = None) -> ProviderResponse: ...

    def get_standings(self, *, league_id: int, season: int) -> ProviderResponse:
        raise NotImplementedError("This provider does not implement standings")

    def get_status(self) -> ProviderResponse:
        raise NotImplementedError("This provider does not implement status")
