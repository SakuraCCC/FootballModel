from pathlib import Path

from app.services.reporting.schemas import ReportType


class PromptLoader:
    _prompt_files = {
        "internal": "internal_report_v2.md",
        "xiaohongshu": "xiaohongshu_v2.md",
        "fact_review": "fact_review_v2.md",
    }

    def __init__(self, prompt_directory: Path | None = None) -> None:
        self._prompt_directory = prompt_directory or Path(__file__).resolve().parents[3] / "prompts"

    def load(self, report_type: ReportType | str) -> str:
        try:
            filename = self._prompt_files[report_type]
        except KeyError as error:
            raise ValueError(f"Unsupported prompt type: {report_type}") from error
        return (self._prompt_directory / filename).read_text(encoding="utf-8")

    def version(self, report_type: ReportType) -> str:
        return self._prompt_files[report_type].removesuffix(".md")
