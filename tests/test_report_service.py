from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1 import reports as reports_api
from app.core.config import Settings
from app.models import ReportOutput
from app.services.prediction.pipeline import PredictionPipeline
from app.services.reporting.builder import ReportContextBuilder
from app.services.reporting.llm_client import OpenAICompatibleLLMClient
from app.services.reporting.service import ReportService
from app.services.reporting.xiaohongshu import DISCLAIMER
from tests.prediction_helpers import create_prediction_dataset
from tests.reporting_helpers import AvailableLLM, UnavailableLLM


def test_report_service_generates_auditable_internal_report(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    report = ReportService(session, llm_client=AvailableLLM()).generate(prediction.id, "internal")

    assert report.status == "generated"
    assert report.prompt_version == "internal_report_v2"
    assert report.llm_model == "test-model"
    assert report.content is not None
    for heading in ("数据截止时间", "来源说明", "数据完整度", "双方分析", "模型结果", "比分复核", "风险说明"):
        assert heading in report.content
    assert session.scalar(select(func.count()).select_from(ReportOutput)) == 1


def test_report_service_returns_llm_unavailable_without_failing(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    report = ReportService(session, llm_client=UnavailableLLM()).generate(prediction.id, "xiaohongshu")

    assert report.status == "llm_unavailable"
    assert report.content is None
    assert report.warnings == ["llm_unavailable"]


def test_openai_compatible_client_does_not_call_network_without_configuration(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    generation = OpenAICompatibleLLMClient(
        Settings(llm_base_url=None, llm_api_key=None, llm_model=None)
    ).generate(prompt="unused", context=ReportContextBuilder(session).build(prediction.id))

    assert generation.status == "llm_unavailable"


def test_xiaohongshu_report_has_disclaimer_and_length_limit(session: Session) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    report = ReportService(session, llm_client=AvailableLLM()).generate(prediction.id, "xiaohongshu")

    assert report.content is not None
    assert DISCLAIMER in report.content
    assert len(report.content) <= 1000
    for heading in ("比赛", "时间", "核心差异", "模型方向", "三个比分", "风险"):
        assert heading in report.content
    assert report.status == "generated"


def test_report_api_persists_and_reads_unavailable_output(
    client: TestClient, session: Session, monkeypatch
) -> None:
    target = create_prediction_dataset(session)
    prediction = PredictionPipeline(session).run(target.id)

    monkeypatch.setattr(
        reports_api,
        "ReportService",
        lambda db_session: ReportService(db_session, llm_client=UnavailableLLM()),
    )
    created = client.post(
        "/api/v1/reports/generate",
        json={"prediction_id": prediction.id, "report_type": "internal"},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "llm_unavailable"
    fetched = client.get(f"/api/v1/reports/{created.json()['report_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["content"] is None
