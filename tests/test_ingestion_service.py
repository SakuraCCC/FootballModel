from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, DataSource, Match, RawDataSnapshot, Team
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.ingestion.service import IngestionService


class FakeProvider(BaseProvider):
    provider_name = "API-Football"
    api_version = "v3"
    source_tier = "secondary"

    def _response(self, endpoint: str, data: list[dict]) -> ProviderResponse:
        now = datetime.now(UTC)
        return ProviderResponse(
            provider=self.provider_name,
            endpoint=endpoint,
            request_time=now,
            retrieved_at=now,
            response_json={"response": data, "errors": {}},
            data=data,
        )

    def get_competitions(self, *, season: int | None = None) -> ProviderResponse:
        return self._response("leagues", [])

    def get_matches(
        self, *, league_id: int, season: int, match_date: str | None = None
    ) -> ProviderResponse:
        return self._response(
            "fixtures",
            [
                {
                    "fixture": {
                        "id": 991,
                        "date": "2026-08-01T12:00:00+00:00",
                        "status": {"short": "NS"},
                    },
                    "league": {"round": "Regular Season"},
                    "teams": {
                        "home": {"id": 101, "name": "PSG"},
                        "away": {"id": 102, "name": "Team B"},
                    },
                }
            ],
        )

    def get_team(self, *, team_id: int) -> ProviderResponse:
        return self._response("teams", [])

    def get_players(self, *, team_id: int, season: int | None = None) -> ProviderResponse:
        return self._response("players", [])

    def get_lineups(self, *, fixture_id: int) -> ProviderResponse:
        return self._response("fixtures/lineups", [])

    def get_injuries(
        self, *, league_id: int, season: int, fixture_id: int | None = None
    ) -> ProviderResponse:
        return self._response("injuries", [])

    def get_statistics(self, *, fixture_id: int, team_id: int | None = None) -> ProviderResponse:
        return self._response("fixtures/statistics", [])


def test_ingestion_persists_normalized_match_source_and_raw_snapshot(session: Session) -> None:
    competition = Competition(
        code="CSL",
        name="Chinese Super League",
        region="China",
        api_football_league_id=169,
        certainty="reported",
    )
    session.add(competition)
    session.commit()

    summary = IngestionService(session, FakeProvider()).sync_matches(
        competition_code="CSL", season=2026, match_date=date(2026, 8, 1)
    )

    stored_match = session.scalar(select(Match))
    source = session.scalar(select(DataSource))
    snapshot = session.scalar(select(RawDataSnapshot))
    stored_team = session.scalar(select(Team).where(Team.external_id == "101"))

    assert summary.saved == 1
    assert summary.quality_levels == {"medium": 1}
    assert source is not None
    assert source.source_name == "API-Football"
    assert snapshot is not None
    assert snapshot.endpoint == "fixtures"
    assert stored_match is not None
    assert stored_match.external_id == "991"
    assert stored_match.certainty == "reported"
    assert stored_team is not None
    assert stored_team.canonical_name == "Paris Saint-Germain"
