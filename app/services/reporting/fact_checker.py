from app.services.reporting.schemas import FactCheckResult, ReportContext


class FactChecker:
    _confirmation_terms = ("官方确认", "已确认", "confirmed")

    def check(self, context: ReportContext, content: str) -> FactCheckResult:
        warnings: list[str] = []
        if context.reported_information and any(term in content for term in self._confirmation_terms):
            warnings.append("reported_information_must_not_be_presented_as_confirmed")
        if context.model_prediction and "模型" not in content:
            warnings.append("model_prediction_must_be_labeled_as_inference")
        if not context.source_snapshots:
            warnings.append("source_snapshot_missing")
        return FactCheckResult(status="warning" if warnings else "passed", warnings=warnings)
