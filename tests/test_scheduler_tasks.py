from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.tasks import scheduler as scheduler_tasks
from app.worker import celery_app
from tests.prediction_helpers import create_prediction_dataset


def test_daily_match_scan_task_uses_persisted_fixtures(session: Session, monkeypatch) -> None:
    target = create_prediction_dataset(session)
    target.kickoff_at = datetime.now(UTC) + timedelta(hours=48)
    session.commit()
    target_id = target.id
    monkeypatch.setattr(scheduler_tasks, "SessionLocal", lambda: session)

    match_ids = scheduler_tasks.daily_match_scan.run()

    assert match_ids == [target_id]


def test_daily_cleanup_removes_only_expired_temporary_files(tmp_path, monkeypatch) -> None:
    expired = tmp_path / "expired.tmp"
    current = tmp_path / "current.tmp"
    expired.write_text("old")
    current.write_text("current")
    old_timestamp = (datetime.now(UTC) - timedelta(days=2)).timestamp()
    import os

    os.utime(expired, (old_timestamp, old_timestamp))
    monkeypatch.setattr(scheduler_tasks, "get_settings", lambda: type("Settings", (), {"temporary_file_dir": Path(tmp_path)})())

    removed = scheduler_tasks.daily_cleanup.run()

    assert removed == 1
    assert not expired.exists()
    assert current.exists()


def test_celery_beat_registers_daily_scheduler_tasks() -> None:
    schedule = celery_app.conf.beat_schedule

    assert schedule["daily-match-scan"]["task"] == "scheduler.daily_match_scan"
    assert schedule["daily-analysis-generation"]["task"] == "scheduler.daily_analysis_generation"
    assert schedule["daily-cleanup"]["task"] == "scheduler.daily_cleanup"
