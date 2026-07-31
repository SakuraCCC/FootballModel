# Production E2E report

## 2026-07-31

Status: not executed in the local environment.

The repository was verified without exposing or inventing credentials. `API_FOOTBALL_KEY` and the LLM configuration were not present, so the controlled command correctly exits with `not_executed` and does not substitute fixtures, mock responses, or fake assets.

Run after production secrets are configured:

```bash
python -m app.cli.e2e_verify --competition CSL --match-id <provider_match_id>
```

Record the JSON output here: `match_id`, `snapshot_ids`, `prediction_id`, `report_id`, `poster_id`, `archive_id`, completeness, model status, LLM status, and poster file status.
