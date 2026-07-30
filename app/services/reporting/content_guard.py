from app.services.reporting.schemas import ContentGuardResult


class ContentGuard:
    _blocked_terms = ("投注", "收益", "稳赚", "串关", "梭哈")
    _required_disclaimer = "本文记录AI足球数据模型的训练、校准与误差分析，仅用于技术交流和比赛讨论，不构成收益或决策建议。"

    def check(self, content: str) -> ContentGuardResult:
        reviewable_content = content.replace(self._required_disclaimer, "")
        found = [term for term in self._blocked_terms if term in reviewable_content]
        if found:
            return ContentGuardResult(
                status="warning", warnings=[f"high_risk_term:{term}" for term in found]
            )
        return ContentGuardResult(status="passed")
