"""Configuration and dependency check; never prints secret values."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.models import SchedulerHeartbeat
from app.services.setup import SetupService
from app.worker import celery_app


def run() -> dict:
    session = SessionLocal()
    try:
        result = SetupService(session).status()
        result["migration"] = "reachable"
        try:
            session.execute(text("SELECT 1"))
        except Exception:
            result["migration"] = "unreachable"
        try:
            get_redis_client().ping()
            result["redis"] = "ok"
        except Exception:
            result["redis"] = "unreachable"
        try:
            result["worker"] = "ok" if celery_app.control.inspect(timeout=1).ping() else "unreachable"
        except Exception:
            result["worker"] = "unreachable"
        try:
            heartbeat = session.scalar(select(SchedulerHeartbeat).order_by(SchedulerHeartbeat.last_executed_at.desc()))
            result["beat"] = "ok" if heartbeat is not None else "unreachable"
        except Exception:
            result["beat"] = "unreachable"
        result["poster_directory"] = "writable" if Path(get_settings().poster_output_dir).exists() else "missing"
        return result
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run Sakura first-run checks").parse_args(argv)
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] not in {"invalid", "unreachable"} for item in result.get("checks", [])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
