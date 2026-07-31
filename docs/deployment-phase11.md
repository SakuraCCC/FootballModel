# Phase 11 deployment and acceptance

1. Copy `.env.production.example` to `.env.production`, set a long random `ADMIN_API_KEY`, database/Redis URLs, and choose `FOOTBALL_DATA_MODE=hybrid`.
2. Run `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`.
3. Run `python -m app.cli.first_run_check`; inspect `/health` publicly and detailed health/setup routes with `X-Admin-API-Key`.
4. Run `python -m app.cli.api_football_audit --dry-run`. It calls only `/status` (and the explicit non-dry audit may check `/leagues`).
5. Use the personal console to select one to three matches, approve reports/posters, and export a batch ZIP.
6. Run `scripts/production_acceptance.sh`. It does not consume provider quota unless `--live-provider-check` is supplied.

The GitHub workflow creates a temporary `.env.production` from the safe example solely because Compose services declare `env_file: .env.production`; it deletes the fixture in an `always()` cleanup step.
