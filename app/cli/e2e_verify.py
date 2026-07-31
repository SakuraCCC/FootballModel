"""Controlled real-data verification; never falls back to fixtures or mock data."""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.version import DISPLAY_VERSION, MODEL_VERSION, POSTER_VERSION, PROMPT_VERSION
from app.models import DataSource, Match, PosterOutput, ProviderQuotaUsage, RawDataSnapshot
from app.services.archive import PredictionArchiveService
from app.services.ingestion import ApiFootballProvider, IngestionService
from app.services.posters import PosterService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting import ReportService


def run(competition: str, match_id: str, *, data_mode: str | None = None, allow_provider: bool = False, offline: bool = False, dry_run: bool = False) -> dict:
    settings = get_settings()
    resolved_mode = "offline" if offline else (data_mode or settings.football_data_mode)
    if dry_run:
        return {
            "status": "not_executed",
            "reason": "dry_run",
            "version": DISPLAY_VERSION,
            "data_mode": resolved_mode,
            "provider_usage": None,
            "model_version": MODEL_VERSION,
            "prompt_version": PROMPT_VERSION,
            "poster_version": POSTER_VERSION,
        }
    if resolved_mode != "offline" and (not allow_provider or settings.api_football_key is None):
        raise RuntimeError("Missing API_FOOTBALL_KEY; live E2E was not executed")
    if resolved_mode != "offline" and (settings.llm_base_url is None or settings.llm_api_key is None or settings.llm_model is None):
        raise RuntimeError("Missing LLM_BASE_URL, LLM_API_KEY, or LLM_MODEL; live E2E was not executed")
    session = SessionLocal()
    try:
        match = session.get(Match, match_id)
        if match is None or match.external_id is None:
            raise RuntimeError("A persisted provider match with external_id is required")
        stats = None
        if resolved_mode != "offline":
            ingestion = IngestionService(session, ApiFootballProvider())
            stats = ingestion.sync_statistics(match_id=match.id, fixture_id=int(match.external_id))
        prediction = PredictionPipeline(session).run(match.id)
        report = ReportService(session).generate(prediction.id, "internal")
        if report.status != "generated":
            raise RuntimeError(f"Report status is {report.status}; live E2E stopped")
        poster = PosterService(session).generate(report.report_id)
        archive = PredictionArchiveService(session).archive(prediction.id)
        poster_record = session.scalar(
            select(PosterOutput).where(PosterOutput.report_id == report.report_id).order_by(PosterOutput.created_at.desc())
        )
        quota = session.scalar(select(ProviderQuotaUsage).order_by(ProviderQuotaUsage.last_checked_at.desc()))
        provider_usage = {
            "request_count": quota.request_count,
            "daily_remaining": quota.daily_remaining,
            "quota_state": quota.quota_state,
        } if quota else None
        snapshots = list(session.scalars(select(RawDataSnapshot.id).join(DataSource, DataSource.id == RawDataSnapshot.data_source_id).where(RawDataSnapshot.provider == "API-Football")))
        return {"match_id": match.id, "competition": competition, "snapshot_ids": snapshots, "prediction_id": prediction.id, "report_id": report.report_id, "poster_id": poster_record.id if poster_record else Path(poster.file_path).stem, "archive_id": archive.id, "version": DISPLAY_VERSION, "data_mode": resolved_mode, "data_completeness": "offline_incomplete" if resolved_mode == "offline" else "persisted", "model_status": prediction.status, "llm_status": report.status, "poster_file_status": Path(poster.file_path).exists(), "statistics_snapshot_id": stats.snapshot_id if stats else None, "provider_request_count": provider_usage["request_count"] if provider_usage else (0 if resolved_mode == "offline" else None), "provider_quota_remaining": provider_usage["daily_remaining"] if provider_usage else None, "provider_usage": provider_usage, "model_version": prediction.model_version or MODEL_VERSION, "prompt_version": report.prompt_version or PROMPT_VERSION, "poster_version": poster_record.poster_version if poster_record else POSTER_VERSION, "missing_fields": ["latest_injuries", "official_lineups", "live_statistics"] if resolved_mode == "offline" else []}
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a controlled real-data production E2E verification")
    parser.add_argument("--competition", required=True)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--data-mode", choices=["api_football", "hybrid", "manual", "offline"], default=None)
    parser.add_argument("--allow-provider", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(args.competition, args.match_id, data_mode=args.data_mode, allow_provider=args.allow_provider, offline=args.offline, dry_run=args.dry_run), ensure_ascii=False, indent=2))
    except RuntimeError as error:
        resolved_mode = "offline" if args.offline else (args.data_mode or get_settings().football_data_mode)
        print(json.dumps({"status": "not_executed", "reason": str(error), "version": DISPLAY_VERSION, "data_mode": resolved_mode, "provider_usage": None, "model_version": MODEL_VERSION, "prompt_version": PROMPT_VERSION, "poster_version": POSTER_VERSION}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
