# Phase 11 operating notes

Phase 11 is the final feature phase. The system now favors existing database snapshots, then fresh API-Football data only when coverage, data freshness and quota allow it. `manual` imports and `offline` mode never call external HTTP. Every imported or provider fact keeps source, timestamp and certainty.

The personal console is `/api/v1/dashboard/admin` and is protected by `X-Admin-API-Key`. `/api/v1/setup/status` returns only configured/missing/invalid/unreachable states. Use `python -m app.cli.api_football_audit --dry-run` for a status-only audit and `python -m app.cli.first_run_check` before deployment.

For a batch, call `POST /api/v1/batches/{batch_id}/export`, then download the returned ZIP. It contains reports, text, PNGs, `summary.json`, `source_manifest.json` and `data_completeness.json`, but never secrets or full provider responses.

After Phase 11, stop adding large features. Run selected real matches, collect actual results, evaluate calibration and decide whether a paid provider plan is justified.
