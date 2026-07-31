#!/usr/bin/env sh
set -eu

live_provider=0
if [ "${1:-}" = "--live-provider-check" ]; then
  live_provider=1
fi

docker compose -f docker-compose.prod.yml --env-file .env.production config >/dev/null
set +e
python -m app.cli.first_run_check
first_run_status=$?
set -e
if [ "$live_provider" -eq 1 ]; then
  python -m app.cli.api_football_audit
else
  set +e
  python -m app.cli.api_football_audit --dry-run
  audit_status=$?
  set -e
  [ "$audit_status" -eq 0 ] || [ "$audit_status" -eq 2 ]
fi
python -m app.cli.e2e_verify --dry-run --offline --competition CSL --match-id "${MATCH_ID:-not-provided}"
echo "production acceptance checks completed (first_run_status=${first_run_status:-0})"
