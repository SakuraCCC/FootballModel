# Sakura Football Model V2.0

Phase 1 establishes the service foundation only: FastAPI, PostgreSQL, Redis, Docker Compose,
Alembic migrations, supported-competition metadata, and a minimal read-only API. It deliberately
contains no prediction model, data-provider integration, mock match data, LLM workflow, poster,
or review dashboard.

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
