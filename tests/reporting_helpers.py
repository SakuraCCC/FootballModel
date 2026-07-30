from app.services.reporting.schemas import LLMGeneration


class AvailableLLM:
    def generate(self, *, prompt, context) -> LLMGeneration:
        return LLMGeneration(status="generated", content="这是模型分析内容，模型方向来自赛前数据。", model="test-model")


class UnavailableLLM:
    def generate(self, *, prompt, context) -> LLMGeneration:
        return LLMGeneration(status="llm_unavailable")
