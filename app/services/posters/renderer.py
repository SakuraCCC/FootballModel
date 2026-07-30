from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.services.posters.schemas import PosterData, PosterStyle
from app.services.posters.template_loader import TemplateLoader


class PosterRenderer:
    """Renders deterministic HTML/CSS match cards to PNG through Playwright."""

    def __init__(
        self,
        *,
        template_loader: TemplateLoader | None = None,
        output_directory: Path | str = "generated/posters",
        playwright_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._template_loader = template_loader or TemplateLoader()
        self._output_directory = Path(output_directory)
        self._playwright_factory = playwright_factory

    def render(self, poster_id: str, style: PosterStyle, data: PosterData) -> Path:
        html = self._template_loader.render(style, data)
        self._output_directory.mkdir(parents=True, exist_ok=True)
        output_path = self._output_directory / f"{poster_id}.png"
        factory = self._playwright_factory or self._default_playwright_factory
        with factory() as playwright:
            # Use the installed Chrome for Testing channel instead of a system browser.
            browser = playwright.chromium.launch(channel="chromium")
            try:
                page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
                page.set_content(html, wait_until="networkidle")
                page.screenshot(path=str(output_path), type="png", full_page=True)
            finally:
                browser.close()
        return output_path.resolve()

    @staticmethod
    def _default_playwright_factory() -> Any:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("Playwright is not installed. Install project dependencies first.") from error
        return sync_playwright()
