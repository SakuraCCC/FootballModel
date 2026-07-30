# Phase 9 real-match end-to-end verification

Status: pending external configuration (2026-07-31).

This repository deliberately does not ship API-Football or LLM credentials. At verification time `API_FOOTBALL_KEY` and the LLM configuration were absent, so no provider request, match prediction, report, or PNG was fabricated.

After credentials are configured, perform one controlled MLS, CSL, or BRA_SERIE_A fixture run: ingest the fixture, run the prediction, generate the fact-checked report, generate the poster, then archive the prediction. Record the resulting `match_id`, `prediction_id`, `report_id`, `poster_id`, source snapshot ID, and health endpoint responses here. This preserves the production evidence chain without exposing secrets.
