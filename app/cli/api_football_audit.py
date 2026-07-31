"""Provider audit with a no-side-effect dry-run mode."""

import argparse
import json
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Competition
from app.services.ingestion import ApiFootballProvider, IngestionService
from app.services.ingestion.api_football import ProviderConfigurationError

TARGET_CODES = ("CSL", "MLS", "LIGA_MX", "UCL_QUALIFIER", "BRA_SERIE_A")


def run(*, dry_run: bool = False) -> dict:
    settings = get_settings()
    if settings.api_football_key is None:
        return {"status": "not_executed", "reason": "missing API_FOOTBALL_KEY"}
    provider = ApiFootballProvider()
    status = provider.get_status()
    item = status.data[0] if status.data else {}
    result = {"status": "ok", "api_key_configured": True, "plan": item.get("account", {}).get("plan", {}) if isinstance(item.get("account"), dict) else {}, "targets": {code: None for code in TARGET_CODES}, "endpoints": ["/status"], "dry_run": dry_run}
    if dry_run:
        result["coverage"] = "not_checked"
        result["estimated_daily_requests"] = {"fixtures": 5, "selected_match_context": 5, "total": 10}
        result["safe_matches_per_day"] = "1-3"
        result["free_plan_sufficient"] = "depends_on_runtime_quota"
        return result
    session = SessionLocal()
    try:
        service = IngestionService(session, provider)
        coverage = {}
        configured = {item.code: item.api_football_league_id for item in session.scalars(select(Competition)).all() if item.code in TARGET_CODES}
        result["targets"].update(configured)
        for code in TARGET_CODES:
            try:
                summary = service.sync_competitions(season=settings.target_season)
                competition = session.scalar(select(Competition).where(Competition.code == code))
                if competition is not None:
                    service._ensure_coverage(competition, settings.target_season, None)
                coverage[code] = {"snapshot_id": summary.snapshot_id, "status": "checked"}
            except Exception as error:
                coverage[code] = {"status": "unavailable", "reason": str(error)}
        result["coverage"] = coverage
        result["endpoints"] = ["/status", "/leagues"]
        result["estimated_daily_requests"] = {"fixture_sync": 5, "standings": 5, "selected_context_per_match": 5, "total_without_cache": 15}
        result["safe_matches_per_day"] = "1-3"
        result["free_plan_sufficient"] = "runtime_dependent"
        return result
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit API-Football endpoints and free-plan budget")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(dry_run=args.dry_run)
    except ProviderConfigurationError as error:
        result = {"status": "not_executed", "reason": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
