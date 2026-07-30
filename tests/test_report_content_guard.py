from app.services.reporting.content_guard import ContentGuard
from app.services.reporting.xiaohongshu import DISCLAIMER


def test_content_guard_flags_high_risk_terms() -> None:
    guard = ContentGuard()

    warning = guard.check("这是稳赚方案，不要错过。")
    passed = guard.check("模型结果仅用于比赛讨论。")
    disclaimer_only = guard.check(DISCLAIMER)

    assert warning.status == "warning"
    assert warning.warnings == ["high_risk_term:稳赚"]
    assert passed.status == "passed"
    assert disclaimer_only.status == "passed"
