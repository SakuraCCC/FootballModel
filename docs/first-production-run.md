# First production run (V3.2)

This runbook records the first real, single-operator execution. It never substitutes mock data when a provider or LLM credential is missing.

## Prerequisites

1. Copy `.env.production.example` to `.env.production` and set `DATABASE_URL`, `REDIS_URL`, `ADMIN_API_KEY`, `API_FOOTBALL_KEY`, and the LLM settings used by the report service.
2. Start the production stack and run `alembic upgrade head`.
3. Run `python -m app.cli.production_check`. `READY` means all five competitions, provider quota, storage, and LLM are available. `PARTIAL_READY` is safe for preparation but not a complete live content run.

## Controlled run

Use the protected personal console or the controlled command:

```text
python -m app.cli.e2e_verify --competition CSL --match-id <persisted-match-id> --data-mode hybrid --allow-provider
```

The chain is:

```text
fixture/context sync -> quality check -> prediction -> report -> poster -> manual approval -> archive
```

The command prints and the operator should record:

| Field | Meaning |
| --- | --- |
| `match_id` | Persisted internal match identifier |
| `snapshot_ids` | Raw provider snapshots used by the run |
| `prediction_id` | Structured model output |
| `report_id` | Internal report output |
| `poster_id` | PNG poster output |
| `archive_id` | Immutable production archive |
| `data_mode` | `api_football`, `hybrid`, `manual`, or `offline` |
| `provider_usage` | Request count, remaining quota, and quota state |
| `model_version` / `prompt_version` / `poster_version` | Reproducibility metadata |

Approve the fact-checked report and poster in the personal console before treating them as final assets. Keep this output with the date and operator notes in `docs/production-e2e-report.md`.

## Missing credentials

Without `API_FOOTBALL_KEY` or a complete LLM configuration, `e2e_verify` returns `not_executed` and explains the missing setting. It does not use fixtures or mock responses. `--dry-run` only validates command routing and reports `not_executed`.

