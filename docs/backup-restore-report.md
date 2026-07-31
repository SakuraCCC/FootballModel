# Backup and restore report

## 2026-07-31

Status: not executed locally because Docker/PostgreSQL are not installed. CI validates script syntax; execute the full test on the VPS with a temporary restore database before accepting production.

The required verification sequence is:

1. Create a PostgreSQL backup with `scripts/backup_postgres.sh`.
2. Set `BACKUP_FILE` and run `scripts/restore_postgres_test.sh` against a temporary database.
3. Read `matches`, `raw_data_snapshots`, `prediction_results`, `report_outputs`, `poster_outputs` and `prediction_archive`.
4. Drop the temporary database and record the result here.
