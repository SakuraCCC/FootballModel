# Production E2E report

## 2026-07-31

Status: not executed in the local environment (`not_executed`).

The repository was verified without exposing or inventing credentials. `API_FOOTBALL_KEY`, `ADMIN_API_KEY`, PostgreSQL/Redis services and the LLM configuration were not present locally, so the controlled command correctly exits with `not_executed` and does not substitute fixtures, mock responses, or fake assets. Docker is also not installed on this workstation, so the production Compose smoke/build remains CI/VPS work.

Run after production secrets are configured:

```bash
python -m app.cli.e2e_verify --competition CSL --match-id <provider_match_id>
```

Use `--allow-provider --data-mode hybrid` for a real provider run, or `--offline` only when the database already contains sufficient historical data. Offline output must remain marked incomplete for current injuries, lineups and live statistics.

Record the JSON output here: `match_id`, `snapshot_ids`, `prediction_id`, `report_id`, `poster_id`, `archive_id`, completeness, model status, LLM status, and poster file status.
