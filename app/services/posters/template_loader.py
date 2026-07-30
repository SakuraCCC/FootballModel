import html
import re
from pathlib import Path

from app.services.posters.schemas import PosterData, PosterStyle


class TemplateLoader:
    _placeholder = re.compile(r"{{\s*([a-z_]+)\s*}}")

    def __init__(self, template_directory: Path | None = None) -> None:
        self._template_directory = template_directory or Path(__file__).resolve().parent / "templates"

    def render(self, style: PosterStyle, data: PosterData) -> str:
        template = (self._template_directory / style.template_name).read_text(encoding="utf-8")
        values = {name: html.escape(str(value)) for name, value in data.__dict__.items()}

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in values:
                raise ValueError(f"Template value is missing: {name}")
            return values[name]

        return self._placeholder.sub(replace, template)
