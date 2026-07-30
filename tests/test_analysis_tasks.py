from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AnalysisJob, AnalysisJobMatch, AnalysisResult
from app.tasks import analysis
from app.worker import celery_app


def test_celery_pipeline_persists_fixed_test_result(monkeypatch, session: Session) -> None:
    task_session_factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(analysis, "SessionLocal", task_session_factory)
    job = AnalysisJob(
        competition_name="中国超级联赛",
        match_date=date(2026, 8, 1),
        model_version="Sakura AI足球预测系统 V2.0",
        poster_style="csl",
        watermark="Sakura Football Model V2.0",
        matches=[AnalysisJobMatch(home_team="测试主队", away_team="测试客队")],
    )
    session.add(job)
    session.commit()

    previous_eager = celery_app.conf.task_always_eager
    previous_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    try:
        analysis.enqueue_analysis_pipeline(job.id)
    finally:
        celery_app.conf.update(
            task_always_eager=previous_eager,
            task_eager_propagates=previous_propagates,
        )

    session.expire_all()
    stored_job = session.scalar(select(AnalysisJob).where(AnalysisJob.id == job.id))
    stored_result = session.scalar(select(AnalysisResult).where(AnalysisResult.job_id == job.id))

    assert stored_job is not None
    assert stored_job.status == "completed"
    assert stored_job.current_step == "completed"
    assert stored_job.error_message is None
    assert stored_result is not None
    assert stored_result.status == "completed"
    assert stored_result.structured_json["mock_for_pipeline_test"] is True
    assert stored_result.structured_json["model_outputs"]["status"] == "not_executed"
    assert stored_result.structured_json["score_review"]["candidate_scores"] == []


def test_validation_failure_records_error_message(monkeypatch, session: Session) -> None:
    task_session_factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(analysis, "SessionLocal", task_session_factory)
    job = AnalysisJob(
        competition_name="中国超级联赛",
        match_date=date(2026, 8, 1),
        model_version="Sakura AI足球预测系统 V2.0",
        poster_style="csl",
        watermark="Sakura Football Model V2.0",
    )
    session.add(job)
    session.commit()

    with pytest.raises(ValueError, match="at least one match is required"):
        analysis.validate_input_task.run(job.id)

    session.expire_all()
    stored_job = session.scalar(select(AnalysisJob).where(AnalysisJob.id == job.id))
    assert stored_job is not None
    assert stored_job.status == "failed"
    assert stored_job.current_step == "validate_input"
    assert stored_job.error_message == "at least one match is required"
