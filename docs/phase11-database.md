# Phase 11 database changes

Migration `20260731_0012` adds:

- `competition_coverages`: competition/season coverage JSON, snapshot, certainty and seven-day expiry.
- `provider_quota_usage` fields for plan, daily/minute limits and remaining values, reset/check time and `quota_state`.
- `raw_data_snapshots.request_hash`, `cached` and `cache_expires_at` for provider request deduplication.
- `import_batches`: source metadata, certainty, importer and original imported records.
- `batch_exports`: generated ZIP path and status.

Existing prediction, reporting, poster and evaluation tables are unchanged. `alembic upgrade head --sql` is the deployment-safe migration check.
