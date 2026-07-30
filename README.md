# Sakura Football Model V2.0

Phase 1 establishes the service foundation only: FastAPI, PostgreSQL, Redis, Docker Compose,
Alembic migrations, supported-competition metadata, and a minimal read-only API. It deliberately
contains no prediction model, data-provider integration, mock match data, LLM workflow, poster,
or review dashboard.

Phase 2 adds an asynchronous Analysis Job lifecycle. It validates a submitted batch, produces a
fixed pipeline-test JSON structure, and persists the result. Every generated result contains
`mock_for_pipeline_test=true`; no football data source, prediction model, LLM, or poster generator
is called.

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
