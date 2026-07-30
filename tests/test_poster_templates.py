from app.services.posters.schemas import PosterData
from app.services.posters.style_manager import StyleManager
from app.services.posters.template_loader import TemplateLoader


def test_all_competition_templates_render_required_values() -> None:
    manager = StyleManager()
    data = PosterData(
        competition_name="测试联赛",
        beijing_time="2026-08-01 20:00",
        home_team="主队 <A>",
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
        accent_color="#000000",
    )
    loader = TemplateLoader()

    for code in manager.supported_codes():
        rendered = loader.render(manager.get(code), data)

        assert "{{" not in rendered
        assert "主队 &lt;A&gt;" in rendered
        assert "Sakura Football Model V2.0" in rendered
