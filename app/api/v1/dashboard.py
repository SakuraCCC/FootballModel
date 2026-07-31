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
def model_performance(competition_code: str | None = None, session: Session = Depends(get_db_session)) -> ModelPerformanceDashboardRead:
    return ModelPerformanceDashboardRead(**DashboardService(session).model_performance(competition_code=competition_code))


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def simple_admin_dashboard(session: Session = Depends(get_db_session)) -> HTMLResponse:
    context = DashboardService(session).admin_context()
    data = context["summary"]
    cards = [
        ("Predictions", data["total_predictions"]),
        ("Reports", data["total_reports"]),
        ("Posters", data["total_posters"]),
        ("Pending", data["today_pending_matches"]),
        ("Data mode", context["data_mode"]),
        ("Plan", context["plan_name"] or "unknown"),
        ("Daily remaining", context["daily_remaining"] if context["daily_remaining"] is not None else "unknown"),
        ("Quota state", context["quota_state"]),
        ("PostgreSQL", context["database_status"]),
        ("Redis", context["redis_status"]),
        ("Worker", context["worker_status"]),
        ("Scheduler", context["scheduler_status"]),
    ]
    cards_html = "".join(f"<div class='card'><small>{label}</small><h2>{value}</h2></div>" for label, value in cards)
    api_state = "configured" if context["api_football_configured"] else "missing"
    llm_state = "configured" if context["llm_configured"] else "missing"
    return HTMLResponse(
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>Sakura personal console</title>"
        "<style>body{font-family:system-ui;max-width:960px;margin:48px auto;background:#101828;color:#e5e7eb}"
        ".card{background:#1f2937;padding:18px;border-radius:10px;min-width:150px}section{display:flex;gap:12px;flex-wrap:wrap}a{color:#7dd3fc}</style>"
        f"<h1>Sakura Football Model personal console</h1><p>API-Football: {api_state} · LLM: {llm_state}</p><section>{cards_html}</section>"
        "<h2>Selected match actions</h2><p><label>Admin key (not stored): <input id='key' type='password'></label> "
        "<select id='competition'><option>CSL</option><option>MLS</option><option>LIGA_MX</option><option>UCL_QUALIFIER</option><option>BRA_SERIE_A</option></select> "
        "<input id='season' value='2026' size='4'></p>"
        "<p><button onclick=sync('fixtures')>Sync fixtures (about 1 request)</button> "
        "<button onclick=sync('standings')>Sync standings (about 1 request)</button> "
        "<button onclick=sync('results')>Sync results (about 1 request)</button></p>"
        "<p id='message'></p><script>async function sync(kind){const key=document.getElementById('key').value;const code=document.getElementById('competition').value;const season=Number(document.getElementById('season').value);const body={competition_code:code,season:season};const r=await fetch('/api/v1/ingestion/api-football/'+kind,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-API-Key':key},body:JSON.stringify(body)});document.getElementById('message').textContent=await r.text()}</script>"
        "<p><a href='/api/v1/dashboard/content-assets'>Content assets</a> · "
        "<a href='/api/v1/dashboard/model-performance'>Model performance</a> · "
        "<a href='/api/v1/automation/failures'>Failed tasks</a> · "
        "<a href='/api/v1/setup/status'>First-run status</a></p></html>"
    )


@router.get("/content-assets", response_model=ContentAssetSummaryRead)
def content_assets(start_date: date | None = None, end_date: date | None = None, competition_code: str | None = None, match_id: str | None = None, session: Session = Depends(get_db_session)) -> ContentAssetSummaryRead:
    return ContentAssetSummaryRead(**DashboardService(session).content_assets(start_date=start_date, end_date=end_date, competition_code=competition_code, match_id=match_id))
