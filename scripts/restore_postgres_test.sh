#!/usr/bin/env sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${BACKUP_FILE:?BACKUP_FILE must point to a .sql or .sql.gz backup}"

restore_db="${POSTGRES_DB}_restore_test_$$"
cleanup() {
  docker compose -f docker-compose.prod.yml exec -T db dropdb -U "$POSTGRES_USER" --if-exists "$restore_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker compose -f docker-compose.prod.yml exec -T db createdb -U "$POSTGRES_USER" "$restore_db"
case "$BACKUP_FILE" in
  *.gz) gzip -dc "$BACKUP_FILE" | docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$restore_db" >/dev/null ;;
  *) docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$restore_db" < "$BACKUP_FILE" >/dev/null ;;
esac
docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$restore_db" -tAc "SELECT count(*) FROM alembic_version" | grep -Eq '^[[:space:]]*[1-9]'
printf 'backup restore smoke passed for %s\n' "$restore_db"
