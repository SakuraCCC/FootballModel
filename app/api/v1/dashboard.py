from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.dashboard import (
    ContentAssetSummaryRead,
    DashboardSummaryRead,
    ModelPerformanceDashboardRead,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryRead)
def dashboard_summary(session: Session = Depends(get_db_session)) -> DashboardSummaryRead:
    return DashboardSummaryRead(**DashboardService(session).summary())


@router.get("/model-performance", response_model=ModelPerformanceDashboardRead)
def model_performance(
    competition_code: str | None = None, session: Session = Depends(get_db_session)
) -> ModelPerformanceDashboardRead:
    return ModelPerformanceDashboardRead(
        **DashboardService(session).model_performance(competition_code=competition_code)
    )


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def simple_admin_dashboard(session: Session = Depends(get_db_session)) -> HTMLResponse:
    data = DashboardService(session).summary()
    return HTMLResponse(
        """<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>Sakura 运营后台</title><style>body{font-family:system-ui;max-width:920px;margin:48px auto;background:#101828;color:#e5e7eb}section{display:flex;gap:12px;flex-wrap:wrap}.card{background:#1f2937;padding:18px;border-radius:10px;min-width:150px}a{color:#7dd3fc}</style><h1>Sakura Football Model</h1><p>轻量运营概览（实时数据库数据）</p><section>"""
        + "".join(
            f"<div class='card'><small>{label}</small><h2>{value}</h2></div>"
            for label, value in [
                ("预测", data["total_predictions"]),
                ("报告", data["total_reports"]),
                ("海报", data["total_posters"]),
                ("待分析", data["today_pending_matches"]),
                ("已完成自动化", data["today_completed_automations"]),
            ]
        )
        + "</section><p><a href='/api/v1/dashboard/content-assets'>内容资产 JSON</a> · <a href='/api/v1/dashboard/model-performance'>模型表现 JSON</a> · <a href='/api/v1/automation/failures'>失败任务 JSON</a></p></html>"
    )


@router.get("/content-assets", response_model=ContentAssetSummaryRead)
def content_assets(
    start_date: date | None = None,
    end_date: date | None = None,
    competition_code: str | None = None,
    match_id: str | None = None,
    session: Session = Depends(get_db_session),
) -> ContentAssetSummaryRead:
    return ContentAssetSummaryRead(
        **DashboardService(session).content_assets(
            start_date=start_date,
            end_date=end_date,
            competition_code=competition_code,
            match_id=match_id,
        )
    )
