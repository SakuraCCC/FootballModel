"""Non-destructive first production readiness check.

The command intentionally returns exit code 0 even when the installation is not
ready.  It is a report for a single operator, not a deployment gate.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Competition
from app.services.ingestion import ApiFootballProvider

TARGET_COMPETITIONS = ("CSL", "MLS", "LIGA_MX", "UCL_QUALIFIER", "BRA_SERIE_A")


def _configured(value: object) -> str:
    return "configured" if value else "missing"


def run() -> dict:
    settings = get_settings()
    environment = {
        "DATABASE": _configured(settings.database_url),
        "REDIS": _configured(settings.redis_url),
        "ADMIN_API_KEY": _configured(settings.admin_api_key),
        "API_FOOTBALL_KEY": _configured(settings.api_football_key),
        "LLM": _configured(settings.llm_base_url and settings.llm_api_key and settings.llm_model),
        "STORAGE": "missing",
    }
    missing: list[str] = []
    storage = Path(settings.poster_output_dir)
    try:
        storage.mkdir(parents=True, exist_ok=True)
        probe = storage / ".production-check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        environment["STORAGE"] = "ready"
    except OSError:
        missing.append("STORAGE is not writable")

    infrastructure = {"database": "unreachable", "redis": "unreachable"}
    session = None
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        infrastructure["database"] = "connected"
    except Exception as error:  # pragma: no cover - depends on deployment services
        missing.append(f"DATABASE unreachable: {error.__class__.__name__}")
    finally:
        if session is not None:
            session.close()
    try:
        from app.core.redis_client import get_redis_client

        get_redis_client().ping()
        infrastructure["redis"] = "connected"
    except Exception as error:  # pragma: no cover - depends on deployment services
        missing.append(f"REDIS unreachable: {error.__class__.__name__}")

    provider: dict[str, object] = {"status": "not_configured", "plan_name": None, "quota_state": "unknown"}
    if settings.api_football_key:
        try:
            response = ApiFootballProvider(settings=settings).get_status()
            item = response.data[0] if response.data and isinstance(response.data[0], dict) else {}
            account = item.get("account", {}) if isinstance(item.get("account"), dict) else {}
            plan = account.get("plan", {}) if isinstance(account.get("plan"), dict) else {}
            requests = item.get("requests", {}) if isinstance(item.get("requests"), dict) else {}
            limit = requests.get("limit_day") or plan.get("quota_per_day")
            current = requests.get("current")
            remaining = limit - current if isinstance(limit, int) and isinstance(current, int) else None
            provider = {
                "status": "healthy",
                "plan_name": plan.get("name"),
                "daily_limit": limit,
                "daily_used": current,
                "daily_remaining": remaining,
                "quota_state": "unknown" if remaining is None else ("quota_exhausted" if remaining <= 0 else "normal"),
            }
        except Exception as error:  # pragma: no cover - live provider dependent
            provider = {"status": "unreachable", "error": error.__class__.__name__, "quota_state": "unknown"}
            missing.append("API-Football provider is unreachable")
    else:
        missing.append("API_FOOTBALL_KEY is missing")

    competitions = {code: "missing" for code in TARGET_COMPETITIONS}
    try:
        if session is None:
            session = SessionLocal()
        rows = session.scalars(select(Competition).where(Competition.code.in_(TARGET_COMPETITIONS))).all()
        for row in rows:
            competitions[row.code] = "configured" if row.api_football_league_id else "missing_league_id"
        missing.extend(f"competition {code} is not configured" for code, state in competitions.items() if state != "configured")
    except Exception:  # pragma: no cover - depends on deployment services
        missing.append("competition configuration cannot be read")
    finally:
        if session is not None:
            session.close()

    critical = all(environment[key] in {"configured", "ready"} for key in ("DATABASE", "REDIS", "ADMIN_API_KEY", "STORAGE"))
    all_optional = environment["API_FOOTBALL_KEY"] == "configured" and environment["LLM"] == "configured" and provider["status"] == "healthy" and all(value == "configured" for value in competitions.values())
    status = "READY" if critical and all_optional else "PARTIAL_READY" if critical else "NOT_READY"
    return {"status": status, "environment": environment, "infrastructure": infrastructure, "provider": provider, "competitions": competitions, "missing": sorted(set(missing))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report Sakura V3.2 production readiness")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.parse_args(argv)
    try:
        result = run()
    except Exception as error:  # the command must never become a deployment blocker
        result = {"status": "NOT_READY", "missing": [f"check failed: {error.__class__.__name__}"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

