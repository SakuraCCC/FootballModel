"""Scheduled real-provider synchronization tasks."""
# ruff: noqa: E702

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import ActualResult, Competition, Match, PredictionEvaluation, PredictionResult
from app.services.evaluation import EvaluationService
from app.services.ingestion import ApiFootballProvider, IngestionService
from app.services.scheduler.heartbeat import record_heartbeat

logger = logging.getLogger(__name__)
TARGET_COMPETITIONS = ("CSL", "MLS", "LIGA_MX", "UCL_QUALIFIER", "BRA_SERIE_A")


def sync_future_fixtures() -> dict[str, int]:
    session = SessionLocal()
    try:
        record_heartbeat(session, "daily_fixture_sync")
        provider = ApiFootballProvider()
        service = IngestionService(session, provider)
        today = datetime.now(UTC).date()
        counts: dict[str, int] = {}
        for offset in range(7):
            day = today + timedelta(days=offset)
            for code in TARGET_COMPETITIONS:
                try:
                    result = service.sync_matches(competition_code=code, season=get_settings().target_season, match_date=day)
                    counts[code] = counts.get(code, 0) + result.saved
                except Exception:
                    logger.exception("fixture_sync_failed", extra={"match_id": None})
        return counts
    finally:
        session.close()


def sync_context() -> dict[str, int]:
    session = SessionLocal()
    try:
        record_heartbeat(session, "daily_context_sync")
        provider = ApiFootballProvider(); service = IngestionService(session, provider)
        counts = {"standings": 0, "results": 0, "injuries": 0}
        for code in TARGET_COMPETITIONS:
            season = get_settings().target_season
            try:
                counts["standings"] += service.sync_standings(competition_code=code, season=season).saved
                counts["results"] += service.sync_results(competition_code=code, season=season).saved
                counts["injuries"] += service.sync_injuries(competition_code=code, season=season).saved
            except Exception:
                logger.exception("context_sync_failed")
        return counts
    finally:
        session.close()


def refresh_pre_match_context() -> int:
    session = SessionLocal()
    try:
        record_heartbeat(session, "pre_match_refresh")
        now = datetime.now(UTC)
        matches = session.scalars(select(Match).where(Match.kickoff_at >= now, Match.kickoff_at <= now + timedelta(hours=24), Match.external_id.is_not(None)))
        provider = ApiFootballProvider(); service = IngestionService(session, provider); count = 0
        for match in matches:
            competition = session.get(Competition, match.competition_id)
            if competition is None:
                continue
            try:
                fixture_id = int(match.external_id)
                service.sync_injuries(competition_code=competition.code, season=get_settings().target_season, fixture_id=fixture_id)
                service.sync_statistics(match_id=match.id, fixture_id=fixture_id)
                if match.kickoff_at - now <= timedelta(hours=2):
                    service.sync_lineups(match_id=match.id, fixture_id=fixture_id)
                count += 1
            except Exception:
                logger.exception("pre_match_refresh_failed", extra={"match_id": match.id})
        return count
    finally:
        session.close()


def sync_post_match_results() -> int:
    session = SessionLocal()
    try:
        record_heartbeat(session, "post_match_result_sync")
        provider = ApiFootballProvider(); service = IngestionService(session, provider); processed = 0
        for code in TARGET_COMPETITIONS:
            try:
                service.sync_results(competition_code=code, season=get_settings().target_season)
            except Exception:
                logger.exception("post_match_result_sync_failed")
        rows = session.execute(select(PredictionResult, ActualResult).join(ActualResult, ActualResult.match_id == PredictionResult.match_id).outerjoin(PredictionEvaluation, PredictionEvaluation.prediction_id == PredictionResult.id).where(PredictionEvaluation.id.is_(None))).all()
        for prediction, actual in rows:
            try:
                EvaluationService(session).evaluate(prediction.id, actual.id); processed += 1
            except Exception:
                logger.exception("post_match_evaluation_failed", extra={"prediction_id": prediction.id, "match_id": prediction.match_id})
        return processed
    finally:
        session.close()
