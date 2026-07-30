from app.services.posters.watermark import WATERMARK_TEXT, watermark_text


def test_watermark_is_fixed_model_identifier() -> None:
    assert watermark_text() == WATERMARK_TEXT == "Sakura Football Model V2.0"
