from __future__ import annotations

import json
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AnalysisJob,
    AutomationRun,
    BatchExport,
    ModelRun,
    PosterOutput,
    PredictionResult,
    RawDataSnapshot,
    ReportOutput,
)


class BatchExportError(ValueError):
    pass


class BatchExportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def export(self, batch_id: str) -> BatchExport:
        output_root = Path(get_settings().poster_output_dir).parent / "batches" / batch_id
        output_root.mkdir(parents=True, exist_ok=True)
        runs = list(self.session.scalars(select(AutomationRun).join(AnalysisJob, AnalysisJob.id == AutomationRun.analysis_job_id).where(AnalysisJob.batch_id == batch_id)))
        if not runs:
            raise BatchExportError("batch_not_found_or_has_no_assets")
        manifest: list[dict] = []
        summary = {"batch_id": batch_id, "asset_count": 0, "approved_count": 0}
        with zipfile.ZipFile(output_root / f"{batch_id}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for index, run in enumerate(runs, start=1):
                if not run.prediction_id:
                    continue
                prediction = self.session.get(PredictionResult, run.prediction_id)
                if prediction is None:
                    continue
                report = self.session.get(ReportOutput, run.report_id) if run.report_id else None
                xiaohongshu = self.session.scalar(select(ReportOutput).where(ReportOutput.prediction_id == prediction.id, ReportOutput.report_type == "xiaohongshu").order_by(ReportOutput.created_at.desc()))
                poster = self.session.get(PosterOutput, run.poster_id) if run.poster_id else None
                prefix = f"match_{index:02d}"
                if report:
                    archive.writestr(f"{prefix}_internal_report.md", self._safe_text(report.content or ""))
                if poster:
                    file_path = Path(poster.file_path)
                    if file_path.exists() and file_path.is_file():
                        archive.write(file_path, f"{prefix}.png")
                archive.writestr(f"{prefix}_xiaohongshu.txt", self._safe_text(xiaohongshu.content if xiaohongshu else ""))
                model_run = self.session.get(ModelRun, prediction.model_run_id)
                snapshot = self.session.get(RawDataSnapshot, model_run.input_snapshot_id) if model_run and model_run.input_snapshot_id else None
                manifest.append({
                    "match_id": prediction.match_id,
                    "prediction_id": prediction.id,
                    "report_id": report.id if report else None,
                    "poster_id": poster.id if poster else None,
                    "report_review_status": report.review_status if report else None,
                    "poster_review_status": poster.review_status if poster else None,
                    "source": {
                        "snapshot_id": snapshot.id if snapshot else None,
                        "provider": snapshot.provider if snapshot else None,
                        "retrieved_at": snapshot.retrieved_at.isoformat() if snapshot else None,
                        "certainty": "reported" if snapshot else "unavailable",
                        "cached": snapshot.cached if snapshot else False,
                        "missing": snapshot is None,
                    },
                })
                summary["asset_count"] += 1
                summary["approved_count"] += int(bool(report and report.review_status == "approved" and poster and poster.review_status == "approved"))
            archive.writestr("summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
            archive.writestr("source_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("data_completeness.json", json.dumps({"status": "see_source_manifest", "missing_assets": sum(item["source"]["missing"] for item in manifest)}, ensure_ascii=False, indent=2))
        existing = self.session.scalar(select(BatchExport).where(BatchExport.batch_id == batch_id))
        if existing is None:
            existing = BatchExport(batch_id=batch_id, file_path=str(output_root / f"{batch_id}.zip"), status="completed")
            self.session.add(existing)
        else:
            existing.file_path = str(output_root / f"{batch_id}.zip")
        self.session.commit()
        return existing

    @staticmethod
    def _safe_text(content: str) -> str:
        settings = get_settings()
        secrets = [settings.admin_api_key, settings.api_football_key, settings.llm_api_key]
        for secret in secrets:
            if secret is not None:
                value = secret.get_secret_value()
                if value:
                    content = content.replace(value, "[REDACTED]")
        return content
