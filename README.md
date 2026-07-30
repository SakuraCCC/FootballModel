# Sakura Football Model V2.0

Sakura AI 足球预测系统 V2.0 现已完成 Phase 1–5：工程基础、Analysis Job、真实数据采集与溯源、预测与回测评估、以及来源保留的 AI 报告生成与事实审校。系统尚不生成海报或前端页面。

Phase 2 的 Analysis Job 仍只生成固定的管线测试 JSON，且每份结果都有
`mock_for_pipeline_test=true`。真实预测需使用 Phase 3 保存的数据和 Phase 4 的预测接口。

## Start with Docker

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`; documentation is at `/docs`.

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/v1/competitions
```

Create a pipeline-test analysis job:

```bash
curl -X POST http://localhost:8000/api/v1/analysis-jobs \
  -H "Content-Type: application/json" \
  -d '{"competition_name":"中国超级联赛","match_date":"2026-08-01","matches":[{"home_team":"球队A","away_team":"球队B"}],"model_version":"Sakura AI足球预测系统 V2.0","poster_style":"csl","watermark":"Sakura Football Model V2.0"}'
```

Use the returned `id` with `GET /api/v1/analysis-jobs/{id}` to track status and
`GET /api/v1/analysis-jobs/{id}/result` once the job is complete.

## Run a prediction

After real matches and historical actual results have been ingested, run a prediction from its saved
match ID. The system returns `not_available` when there is not enough persisted history; it does not
invent missing input data.

```bash
curl -X POST http://localhost:8000/api/v1/predictions/run \
  -H "Content-Type: application/json" \
  -d '{"match_id":"<saved-match-id>"}'
```

Use the returned `prediction_id` with `GET /api/v1/predictions/{prediction_id}`.

## Generate a report

Set `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL` in `.env` for an OpenAI-compatible endpoint. Keys remain local and must not be committed. Without these settings, report generation returns `llm_unavailable` without failing.

```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"prediction_id":"<prediction-id>","report_type":"internal"}'
```

Use the returned `report_id` with `GET /api/v1/reports/{report_id}`. Set `report_type` to `xiaohongshu` to produce the constrained social-text version.

The initial migration creates the foundation schema and inserts only five supported-competition
metadata records: `CSL`, `MLS`, `LIGA_MX`, `UCL_QUALIFIER`, and `BRA_SERIE_A`.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate  # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload
```

`DATABASE_URL` and `REDIS_URL` must point to reachable local services outside Docker.

## Validation

```bash
ruff check .
pytest
```

GitHub Actions runs linting, migrations, and tests against PostgreSQL and Redis.
