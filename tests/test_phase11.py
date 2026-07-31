from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import httpx
from pydantic import SecretStr
from sqlalchemy import select

from app.cli import api_football_audit, e2e_verify
from app.core.config import Settings
from app.models import (
    AnalysisJob,
    AutomationRun,
    Competition,
    DataSource,
    RawDataSnapshot,
    ReportOutput,
)
from app.services.batch_export import BatchExportService
from app.services.ingestion.api_football import ApiFootballProvider
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.ingestion.service import IngestionError, IngestionService
from app.services.manual_import import ManualImportService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.source_selection import SourceFact, SourceSelector


def response(endpoint: str, data: list[dict], quota: dict | None = None) -> ProviderResponse:
    now = datetime.now(UTC)
    return ProviderResponse("API-Football", endpoint, now, now, {"response": data, "errors": {}}, data, quota or {})


class CoverageProvider(BaseProvider):
    provider_name = "API-Football"
    api_version = "v3"
    source_tier = "secondary"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_status(self):
        self.calls.append("status")
        return response("status", [{"account": {"plan": {"name": "Free"}}, "requests": {"current": 1, "limit_day": 100}}])

    def get_competitions(self, *, season=None):
        self.calls.append("leagues")
        return response("leagues", [{"league": {"id": 169}, "coverage": {"standings": False}}])

    def get_matches(self, *, league_id, season, match_date=None):
        self.calls.append("fixtures")
        return response("fixtures", [])

    def get_team(self, *, team_id):
        return response("teams", [])

    def get_players(self, *, team_id, season=None):
        self.calls.append("players")
        return response("players", [])

    def get_lineups(self, *, fixture_id):
        return response("fixtures/lineups", [])

    def get_injuries(self, *, league_id, season, fixture_id=None):
        return response("injuries", [])

    def get_statistics(self, *, fixture_id, team_id=None):
        return response("fixtures/statistics", [])

    def get_standings(self, *, league_id, season):
        self.calls.append("standings")
        return response("standings", [])


def test_provider_parses_rate_limit_headers_case_insensitively() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "9", "X-RateLimit-Limit-Minute": "10", "X-RateLimit-Remaining-Minute": "2"}, json={"response": [], "errors": {}})

    provider = ApiFootballProvider(settings=Settings(api_football_key=SecretStr("test"), provider_max_retries=0), client=httpx.Client(transport=httpx.MockTransport(handler)))
    quota = provider.get_competitions().quota
    assert quota["x-ratelimit-requests-limit"] == "100"
    assert quota["x-ratelimit-requests-remaining"] == "9"
    assert quota["x-ratelimit-requests-limit-minute"] == "10"
    assert quota["x-ratelimit-requests-remaining-minute"] == "2"


def test_coverage_blocks_unsupported_optional_request(session) -> None:
    session.add(Competition(code="CSL", name="CSL", region="CN", api_football_league_id=169, certainty="reported"))
    session.commit()
    provider = CoverageProvider()
    try:
        IngestionService(session, provider).sync_standings(competition_code="CSL", season=2026)
    except IngestionError as error:
        assert "coverage_unavailable" in str(error)
    else:
        raise AssertionError("coverage must block unsupported standings")
    assert provider.calls == ["leagues"]


def test_provider_status_is_cached(session) -> None:
    provider = CoverageProvider()
    service = IngestionService(session, provider)
    first = service.provider_status()
    second = service.provider_status()
    assert first["plan_name"] == "Free"
    assert second["cached"] is True
    assert provider.calls == ["status"]


def test_manual_import_preserves_provenance_and_csv(session) -> None:
    session.add(Competition(code="CSL", name="CSL", region="CN", api_football_league_id=169, certainty="reported"))
    session.commit()
    result = ManualImportService(session).import_records("matches", {"source_name": "Official CSV", "format": "csv", "payload": "competition_code,season,home_team,away_team,match_id\nCSL,2026,Home FC,Away FC,1"})
    assert result["certainty"] == "reported"
    assert session.scalar(select(RawDataSnapshot).where(RawDataSnapshot.provider == "manual")) is not None
    assert session.scalar(select(DataSource).where(DataSource.source_name == "Official CSV")) is not None


def test_audit_dry_run_and_e2e_dry_run_do_not_require_keys(monkeypatch, capsys) -> None:
    monkeypatch.setattr(api_football_audit, "get_settings", lambda: Settings(api_football_key=None))
    assert api_football_audit.main(["--dry-run"]) == 2
    assert "not_executed" in capsys.readouterr().out
    assert e2e_verify.main(["--competition", "CSL", "--match-id", "x", "--dry-run"]) == 0
    assert "dry_run" in capsys.readouterr().out


def test_ci_creates_temporary_production_env() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "Prepare production env for compose validation" in workflow
    assert "cp .env.production.example .env.production" in workflow
    assert "rm -f .env.production" in workflow


def test_data_mode_switch_is_validated(client, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "football_data_mode", "offline")
    response = client.post("/api/v1/setup/data-mode", json={"mode": "manual"})
    assert response.status_code == 200
    assert response.json()["data_mode"] == "manual"


def test_source_selection_preserves_certainty_and_flags_conflict() -> None:
    now = datetime.now(UTC)
    chosen, conflict = SourceSelector.choose([
        SourceFact("official-value", "official_manual", "official", now),
        SourceFact("reported-value", "api_football", "reported", now),
    ])
    assert chosen is not None and chosen.certainty == "official"
    assert conflict is True


def test_batch_export_contains_manifest_without_secrets(session) -> None:
    from tests.prediction_helpers import create_prediction_dataset

    match = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(match.id)
    report = ReportOutput(prediction_id=prediction.id, report_type="internal", content="analysis", prompt_version="test", status="generated", warnings=[])
    session.add(report)
    session.flush()
    batch = AnalysisJob(competition_name="CSL", match_date=match.kickoff_at.date(), model_version="test", poster_style="csl", watermark="test")
    session.add(batch)
    session.flush()
    session.add(AutomationRun(match_id=match.id, analysis_job_id=batch.id, prediction_id=prediction.id, report_id=report.id, status="completed", current_step="archived"))
    session.commit()
    exported = BatchExportService(session).export(batch.batch_id)
    with ZipFile(exported.file_path) as archive:
        names = archive.namelist()
        assert "source_manifest.json" in names
        content = "".join(archive.read(name).decode("utf-8", errors="ignore") for name in names if name.endswith((".json", ".md", ".txt")))
        assert "ADMIN_API_KEY" not in content
