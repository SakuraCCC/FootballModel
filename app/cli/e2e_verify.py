"""Controlled real-data verification; never falls back to fixtures or mock data."""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import DataSource, Match, RawDataSnapshot
from app.services.archive import PredictionArchiveService
from app.services.ingestion import ApiFootballProvider, IngestionService
from app.services.posters import PosterService
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting import ReportService


def run(competition: str, match_id: str) -> dict:
    settings = get_settings()
    if settings.api_football_key is None:
        raise RuntimeError("Missing API_FOOTBALL_KEY; live E2E was not executed")
    if settings.llm_base_url is None or settings.llm_api_key is None or settings.llm_model is None:
        raise RuntimeError("Missing LLM_BASE_URL, LLM_API_KEY, or LLM_MODEL; live E2E was not executed")
    session = SessionLocal()
    try:
        match = session.get(Match, match_id)
        if match is None or match.external_id is None:
            raise RuntimeError("A persisted provider match with external_id is required")
        ingestion = IngestionService(session, ApiFootballProvider())
        stats = ingestion.sync_statistics(match_id=match.id, fixture_id=int(match.external_id))
        prediction = PredictionPipeline(session).run(match.id)
        report = ReportService(session).generate(prediction.id, "internal")
        if report.status != "generated":
            raise RuntimeError(f"Report status is {report.status}; live E2E stopped")
        poster = PosterService(session).generate(report.report_id)
        archive = PredictionArchiveService(session).archive(prediction.id)
        snapshots = list(session.scalars(select(RawDataSnapshot.id).join(DataSource, DataSource.id == RawDataSnapshot.data_source_id).where(RawDataSnapshot.provider == "API-Football")))
        return {"match_id": match.id, "competition": competition, "snapshot_ids": snapshots, "prediction_id": prediction.id, "report_id": report.report_id, "poster_id": Path(poster.file_path).stem, "archive_id": archive.id, "data_completeness": "persisted", "model_status": prediction.status, "llm_status": report.status, "poster_file_status": Path(poster.file_path).exists(), "statistics_snapshot_id": stats.snapshot_id}
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a controlled real-data production E2E verification")
    parser.add_argument("--competition", required=True)
    parser.add_argument("--match-id", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(args.competition, args.match_id), ensure_ascii=False, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "not_executed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
