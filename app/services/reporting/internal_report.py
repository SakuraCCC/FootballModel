from app.services.reporting.schemas import ReportContext


def append_internal_audit_sections(content: str, context: ReportContext) -> str:
    """Ensure every generated internal report includes its mandatory audit sections."""
    source_times = ", ".join(item.retrieved_at.isoformat() for item in context.source_snapshots) or "未提供"
    required = {
        "数据截止时间": source_times,
        "来源说明": _sources(context),
        "数据完整度": context.data_completeness,
        "双方分析": "球队比较仅基于已保存的赛前数据。",
        "模型结果": _model_summary(context),
        "比分复核": str(context.score_review),
        "风险说明": "；".join(context.risk_warning) or "请结合数据缺失和模型误差审慎解读。",
    }
    missing = [f"## {heading}\n{value}" for heading, value in required.items() if heading not in content]
    return "\n\n".join([content.strip(), *missing]).strip()


def _sources(context: ReportContext) -> str:
    if not context.source_snapshots:
        return "无可用原始数据快照。"
    return "；".join(
        f"{item.provider} / {item.endpoint} / {item.retrieved_at.isoformat()}"
        for item in context.source_snapshots
    )


def _model_summary(context: ReportContext) -> str:
    prediction = context.model_prediction
    return (
        f"模型推断方向：{prediction.get('direction')}；"
        f"候选比分：{prediction.get('primary_score')}、{prediction.get('stable_score')}、"
        f"{prediction.get('alternative_score')}；置信度：{context.confidence}。"
    )
