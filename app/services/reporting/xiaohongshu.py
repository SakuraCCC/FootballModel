from app.services.reporting.schemas import ReportContext

DISCLAIMER = "本文记录AI足球数据模型的训练、校准与误差分析，仅用于技术交流和比赛讨论，不构成收益或决策建议。"


def finalize_xiaohongshu(content: str, context: ReportContext) -> str:
    """Keep the social version concise and append its non-negotiable disclaimer."""
    required_lines = {
        "比赛": f"比赛：{context.match_info.get('home_team')} vs {context.match_info.get('away_team')}",
        "时间": f"时间：{context.match_info.get('kickoff_at')}",
        "核心差异": "核心差异：以已保存的赛前数据为准。",
        "模型方向": f"模型方向：{context.model_prediction.get('direction')}（模型推断）",
        "三个比分": (
            f"三个比分：{context.model_prediction.get('primary_score')}、"
            f"{context.model_prediction.get('stable_score')}、"
            f"{context.model_prediction.get('alternative_score')}"
        ),
        "风险": f"风险：{'；'.join(context.risk_warning) or '数据不足会降低置信度。'}",
    }
    limit = 1000 - len(DISCLAIMER) - 2
    required_section = "\n".join(required_lines.values())
    generated_content = content.strip().replace(DISCLAIMER, "").strip()
    remaining = max(0, limit - len(required_section) - 1)
    body = "\n".join([generated_content[:remaining].rstrip(), required_section]).strip()
    return f"{body[:limit].rstrip()}\n\n{DISCLAIMER}"
