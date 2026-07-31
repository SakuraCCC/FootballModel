from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.version import DATA_VERSION, FEATURE_VERSION, MODEL_VERSION, POSTER_VERSION
from app.models import PosterOutput, PredictionResult, ReportOutput
from app.services.reporting.builder import ReportContextBuilder
from app.services.reporting.content_guard import ContentGuard
from app.services.reporting.fact_checker import FactChecker
from app.services.reporting.internal_report import append_internal_audit_sections
from app.services.reporting.llm_client import OpenAICompatibleLLMClient, ReportLLMClient
from app.services.reporting.prompt_loader import PromptLoader
from app.services.reporting.schemas import GeneratedReport, ReportType
from app.services.reporting.xiaohongshu import finalize_xiaohongshu


class ReportService:
    def __init__(
        self,
        session: Session,
        *,
        llm_client: ReportLLMClient | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._session = session
        self._llm_client = llm_client or OpenAICompatibleLLMClient()
        self._prompt_loader = prompt_loader or PromptLoader()

    def generate(self, prediction_id: str, report_type: ReportType) -> GeneratedReport:
        context = ReportContextBuilder(self._session).build(prediction_id)
        prompt = self._prompt_loader.load(report_type)
        generation = self._llm_client.generate(prompt=prompt, context=context)
        prompt_version = self._prompt_loader.version(report_type)
        prediction = self._session.get(PredictionResult, prediction_id)
        if generation.status == "llm_unavailable":
            output = ReportOutput(
                prediction_id=prediction_id,
                report_type=report_type,
                content=None,
                prompt_version=prompt_version,
                llm_model=None,
                status="llm_unavailable",
                warnings=["llm_unavailable"],
                review_status="draft",
                model_version=prediction.model_version if prediction else MODEL_VERSION,
                feature_version=prediction.feature_version if prediction else FEATURE_VERSION,
                data_version=prediction.data_version if prediction else DATA_VERSION,
                poster_version=POSTER_VERSION,
            )
            self._session.add(output)
            self._session.commit()
            self._session.refresh(output)
            return self._to_generated(output)
        content = self._finalize_content(report_type, generation.content or "", context)
        fact_result = FactChecker().check(context, content)
        guard_result = ContentGuard().check(content)
        warnings = [*fact_result.warnings, *guard_result.warnings]
        output = ReportOutput(
            prediction_id=prediction_id,
            report_type=report_type,
            content=content,
            prompt_version=prompt_version,
            llm_model=generation.model,
            status="warning" if warnings else "generated",
            warnings=warnings,
            review_status="fact_checked" if not warnings else "draft",
            model_version=prediction.model_version if prediction else MODEL_VERSION,
            feature_version=prediction.feature_version if prediction else FEATURE_VERSION,
            data_version=prediction.data_version if prediction else DATA_VERSION,
            poster_version=POSTER_VERSION,
        )
        self._session.add(output)
        self._session.commit()
        self._session.refresh(output)
        return self._to_generated(output)

    def review(self, report_id: str, status: str, notes: str | None = None) -> GeneratedReport:
        if status not in {"approved", "rejected"}:
            raise ValueError("Invalid review status")
        output = self._session.get(ReportOutput, report_id)
        if output is None:
            raise ValueError("Report was not found")
        if status == "approved" and output.review_status not in {"fact_checked", "approved"}:
            raise ValueError("Only fact-checked reports can be approved")
        output.review_status = status
        output.reviewed_at = datetime.now(UTC)
        output.review_notes = notes
        posters = self._session.query(PosterOutput).filter(PosterOutput.report_id == output.id).all()
        for poster in posters:
            poster.review_status = status
            poster.reviewed_at = output.reviewed_at
            poster.review_notes = notes
        self._session.commit()
        self._session.refresh(output)
        return self._to_generated(output)

    def get(self, report_id: str) -> GeneratedReport:
        output = self._session.get(ReportOutput, report_id)
        if output is None:
            raise ValueError("Report was not found")
        return self._to_generated(output)

    @staticmethod
    def _finalize_content(report_type: ReportType, content: str, context) -> str:
        if report_type == "internal":
            return append_internal_audit_sections(content, context)
        return finalize_xiaohongshu(content, context)

    @staticmethod
    def _to_generated(output: ReportOutput) -> GeneratedReport:
        return GeneratedReport(
            report_id=output.id,
            prediction_id=output.prediction_id,
            report_type=output.report_type,
            content=output.content,
            prompt_version=output.prompt_version,
            llm_model=output.llm_model,
            status=output.status,
            warnings=output.warnings,
            review_status=output.review_status,
            reviewed_at=output.reviewed_at,
            review_notes=output.review_notes,
            created_at=output.created_at,
            model_version=output.model_version,
            feature_version=output.feature_version,
            data_version=output.data_version,
            poster_version=output.poster_version,
        )
