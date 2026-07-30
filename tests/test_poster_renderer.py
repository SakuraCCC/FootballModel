import pytest

from app.services.posters.renderer import PosterRenderer
from app.services.posters.schemas import PosterData
from app.services.posters.style_manager import StyleManager
from tests.poster_helpers import FakePlaywright


def test_renderer_writes_png_from_html_template(tmp_path) -> None:
    renderer = PosterRenderer(output_directory=tmp_path, playwright_factory=FakePlaywright)
    data = PosterData(
        competition_name="中国超级联赛",
        beijing_time="2026-08-01 20:00",
        home_team="主队",
        away_team="客队",
        direction="home_win_tendency",
        goal_range="2-4",
        btts_tendency="倾向双方均进球",
        primary_score="2-1",
        stable_score="1-1",
        alternative_score="1-0",
        risk_level="中",
        confidence="medium",
        watermark="Sakura Football Model V2.0",
        accent_color="#E53935",
    )

    output = renderer.render("poster-id", StyleManager().get("CSL"), data)

    assert output.name == "poster-id.png"
    assert output.read_bytes().startswith(b"\x89PNG")


def test_renderer_writes_real_playwright_png_when_chromium_is_available(tmp_path) -> None:
    data = PosterData(
        competition_name="中国超级联赛",
        beijing_time="2026-08-01 20:00",
        home_team="主队",
        away_team="客队",
        direction="home_win_tendency",
        goal_range="2-4",
        btts_tendency="倾向双方均进球",
        primary_score="2-1",
        stable_score="1-1",
        alternative_score="1-0",
        risk_level="中",
        confidence="medium",
        watermark="Sakura Football Model V2.0",
        accent_color="#E53935",
    )
    try:
        output = PosterRenderer(output_directory=tmp_path).render(
            "real-poster", StyleManager().get("CSL"), data
        )
    except RuntimeError as error:
        pytest.skip(str(error))
    except Exception as error:
        if "Executable doesn't exist" in str(error):
            pytest.skip(str(error))
        raise

    assert output.read_bytes().startswith(b"\x89PNG")
