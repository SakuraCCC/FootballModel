"""Small operational reporting services used by the V3.2 launch surface."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AutomationRun,
    DailyOperationReport,
    PosterOutput,
    PromptExperiment,
    ProviderQuotaUsage,
    ReportOutput,
)


class PromptExperimentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        change_description: str,
        related_reports: list[str] | None = None,
        performance_notes: str | None = None,
    ) -> PromptExperiment:
        experiment = PromptExperiment(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            change_description=change_description,
            related_reports=related_reports or [],
            performance_notes=performance_notes,
        )
        self._session.add(experiment)
        self._session.commit()
        self._session.refresh(experiment)
        return experiment


class DailyOperationReportService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_build(self, report_date: date | None = None) -> DailyOperationReport:
        target_date = report_date or datetime.now(UTC).date()
        existing = self._session.scalar(
            select(DailyOperationReport).where(DailyOperationReport.report_date == target_date)
        )
        values = self._metrics(target_date)
        if existing is None:
            existing = DailyOperationReport(report_date=target_date, **values)
            self._session.add(existing)
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def _metrics(self, target_date: date) -> dict[str, int | str]:
        start = datetime.combine(target_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        run_filter = (AutomationRun.created_at >= start, AutomationRun.created_at < end)
        report_filter = (ReportOutput.created_at >= start, ReportOutput.created_at < end)
        poster_filter = (PosterOutput.created_at >= start, PosterOutput.created_at < end)
        analysis_count = self._session.scalar(
            select(func.count()).select_from(AutomationRun).where(*run_filter)
        ) or 0
        successful = self._session.scalar(
            select(func.count()).select_from(AutomationRun).where(*run_filter, AutomationRun.status == "completed")
        ) or 0
        failed = self._session.scalar(
            select(func.count()).select_from(AutomationRun).where(*run_filter, AutomationRun.status == "failed")
        ) or 0
        report_count = self._session.scalar(
            select(func.count()).select_from(ReportOutput).where(*report_filter)
        ) or 0
        poster_count = self._session.scalar(
            select(func.count()).select_from(PosterOutput).where(*poster_filter)
        ) or 0
        quota = self._session.scalar(
            select(ProviderQuotaUsage)
            .where(ProviderQuotaUsage.usage_date == target_date)
            .order_by(ProviderQuotaUsage.last_checked_at.desc(), ProviderQuotaUsage.updated_at.desc())
        )
        return {
            "analysis_match_count": int(analysis_count),
            "successful_tasks": int(successful),
            "failed_tasks": int(failed),
            "provider_request_count": int(quota.request_count if quota else 0),
            "quota_state": quota.quota_state if quota else "unknown",
            "report_count": int(report_count),
            "poster_count": int(poster_count),
        }

