import pytest

from app.services.reporting.prompt_loader import PromptLoader


def test_prompt_loader_reads_versioned_prompt_files() -> None:
    loader = PromptLoader()

    prompt = loader.load("internal")

    assert "数据截止时间" in prompt
    assert loader.version("xiaohongshu") == "xiaohongshu_v2"
    with pytest.raises(ValueError, match="Unsupported prompt type"):
        loader.load("unknown")
