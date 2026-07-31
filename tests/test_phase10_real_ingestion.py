from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.cli import e2e_verify
from app.core.config import Settings
from app.core.security import is_admin_key_valid
from app.main import create_app
from app.models import (
    Competition,
    CompetitionStanding,
    Injury,
    Match,
    MatchLineup,
    MatchStatistic,
    PlayerSeasonStat,
    ProviderQuotaUsage,
    RawDataSnapshot,
)
from app.services.ingestion.api_football import ApiFootballProvider
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.ingestion.service import IngestionService
from app.services.reporting.service import ReportService
from tests.prediction_helpers import create_prediction_dataset
from tests.reporting_helpers import AvailableLLM


def test_api_provider_retries_429_and_returns_quota() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, headers={"x-ratelimit-requests-remaining": "99"}, json={"response": [], "errors": {}})

    provider = ApiFootballProvider(
        settings=Settings(api_football_key=SecretStr("test"), provider_max_retries=1, provider_retry_backoff_seconds=0),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = provider.get_competitions()

    assert calls == 2
    assert result.quota == {"x-ratelimit-requests-remaining": "99"}


class ContextProvider(BaseProvider):
    provider_name = "API-Football"
    api_version = "v3"
    source_tier = "secondary"

    def _response(self, endpoint: str, data: list[dict]) -> ProviderResponse:
        now = datetime.now(UTC)
        return ProviderResponse(self.provider_name, endpoint, now, now, {"response": data, "errors": {}}, data, {"x-ratelimit-requests-remaining": "88"})

    def get_competitions(self, *, season=None):
        return self._response("leagues", [])

    def get_matches(self, *, league_id, season, match_date=None):
        return self._response("fixtures", [{"fixture": {"id": 500, "date": "2026-08-01T12:00:00+00:00", "status": {"short": "FT"}}, "league": {"round": "Regular Season"}, "teams": {"home": {"id": 1, "name": "Home FC"}, "away": {"id": 2, "name": "Away FC"}}, "goals": {"home": 2, "away": 1}}])

    def get_team(self, *, team_id):
        return self._response("teams", [])

    def get_players(self, *, team_id, season=None):
        return self._response("players", [{"player": {"id": 10, "name": "Player A"}, "statistics": [{"games": {"minutes": 900, "appearences": 10, "position": "Forward"}, "goals": {"total": 4, "assists": 2}}]}])

    def get_lineups(self, *, fixture_id):
        return self._response("fixtures/lineups", [{"team": {"id": 1, "name": "Home FC"}, "startXI": [{"player": {"id": 10, "name": "Player A", "pos": "F", "number": 9}}], "substitutes": []}])

    def get_injuries(self, *, league_id, season, fixture_id=None):
        return self._response("injuries", [{"player": {"id": 10, "name": "Player A", "type": "Muscle", "reason": "Reported"}, "team": {"id": 1, "name": "Home FC"}}])

    def get_statistics(self, *, fixture_id, team_id=None):
        return self._response("fixtures/statistics", [{"team": {"id": 1, "name": "Home FC"}, "statistics": [{"type": "Total Shots", "value": 10}, {"type": "Shots on Goal", "value": 4}, {"type": "Ball Possession", "value": "55%"}, {"type": "Corner Kicks", "value": 5}, {"type": "Expected Goals", "value": 1.2}]}])

    def get_standings(self, *, league_id, season):
        return self._response("standings", [{"league": {"standings": [[{"rank": 1, "points": 20, "goalsDiff": 8, "form": "WWD", "team": {"id": 1, "name": "Home FC"}, "all": {"goals": {"for": 15, "against": 7}}}]]}}])


def test_context_ingestion_persists_snapshots_quota_and_null_safe_fields(session: Session) -> None:
    competition = Competition(code="CSL", name="Chinese Super League", region="China", api_football_league_id=169, certainty="reported")
    session.add(competition)
    session.commit()
    service = IngestionService(session, ContextProvider())
    service.sync_standings(competition_code="CSL", season=2026)
    service.sync_players(team_id=1, season=2026)
    service.sync_injuries(competition_code="CSL", season=2026)
    service.sync_results(competition_code="CSL", season=2026)
    match = session.scalar(select(Match))
    service.sync_lineups(match_id=match.id, fixture_id=500)
    service.sync_statistics(match_id=match.id, fixture_id=500)
    service.sync_lineups(match_id=match.id, fixture_id=500)
    service.sync_injuries(competition_code="CSL", season=2026, fixture_id=500)

    assert session.scalar(select(CompetitionStanding)) is not None
    assert session.scalar(select(PlayerSeasonStat)) is not None
    assert session.scalar(select(Injury)) is not None
    assert session.scalar(select(MatchLineup)) is not None
    assert match.lineup_status == "reported"
    statistics = session.scalar(select(MatchStatistic))
    assert statistics.shots == 10 and statistics.xga is None
    assert session.scalar(select(ProviderQuotaUsage)).request_count == 8
    assert session.scalar(select(RawDataSnapshot)) is not None


def test_admin_key_validation_and_health_public(monkeypatch, session: Session) -> None:
    settings = Settings(admin_api_key=SecretStr("secret"))
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings)
    application = create_app()

    def override_session():
        yield session

    application.dependency_overrides[get_db_session] = override_session
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/dashboard/admin").status_code == 401
        assert client.get("/api/v1/dashboard/admin", headers={"X-Admin-API-Key": "secret"}).status_code == 200
    assert is_admin_key_valid("secret", settings.admin_api_key)
    assert not is_admin_key_valid("wrong", settings.admin_api_key)


def test_report_review_workflow(client: TestClient, session: Session) -> None:
    target = create_prediction_dataset(session)
    from app.services.prediction.pipeline import PredictionPipeline

    prediction = PredictionPipeline(session).run(target.id)
    report = ReportService(session, llm_client=AvailableLLM()).generate(prediction.id, "internal")
    approved = client.post(f"/api/v1/reports/{report.report_id}/approve", json={"notes": "checked"})

    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["review_notes"] == "checked"


def test_e2e_cli_stops_without_live_credentials(monkeypatch, capsys) -> None:
    monkeypatch.setattr(e2e_verify, "get_settings", lambda: Settings(api_football_key=None, llm_base_url=None, llm_api_key=None, llm_model=None))

    assert e2e_verify.main(["--competition", "CSL", "--match-id", "real-match"]) == 2
    assert "not_executed" in capsys.readouterr().err
