#!/usr/bin/env sh
set -eu

base_url="${BASE_URL:-http://localhost:8000}"
curl --fail --silent --show-error "$base_url/health" >/dev/null
if [ -n "${ADMIN_API_KEY:-}" ]; then
  curl --fail --silent --show-error -H "X-Admin-API-Key: $ADMIN_API_KEY" "$base_url/database-health" >/dev/null
else
  curl --fail --silent --show-error "$base_url/database-health" >/dev/null
fi
if command -v pg_isready >/dev/null 2>&1; then
  pg_isready -h "${PGHOST:-localhost}" -p "${PGPORT:-5432}" -U "${POSTGRES_USER:-football_model}" >/dev/null
fi
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping | grep -q PONG
fi
printf 'production smoke checks passed\n'
