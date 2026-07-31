# API-Football endpoint audit (Phase 11)

The only third-party HTTP client is `app/services/ingestion/api_football.py`. Business code calls `IngestionService`, which now applies data-mode checks, request hashing, snapshot caching, quota gates and coverage checks before invoking the provider.

| Endpoint | Internal method | Parameters | Use / timing | Core? | Cache | Coverage / notes |
|---|---|---|---|---|---|---|
| `/status` | `ApiFootballProvider.get_status` / `IngestionService.provider_status` | none | at most once per 24h and on explicit audit | optional | 24h | Reads account/plan and request limits; no secret is logged |
| `/leagues` | `get_competitions` / `sync_competitions` | `season` | competition mapping and per-season coverage | core for coverage | 7d | A missing coverage flag blocks the corresponding optional call |
| `/fixtures` | `get_matches` / `sync_matches`, `sync_results` | `league`, `season`, optional `date` | future fixtures and selected post-match results | core | 12h | Result sync is scoped to pending evaluations; no provider `/predictions` |
| `/teams` | `get_team` | `id` | team metadata when explicitly requested | optional | 30d | Null fields remain unavailable |
| `/players` | `get_players` / `sync_players` | `team`, `season` | selected match teams only | optional | 7d | Never full-league daily sync; blocked by `coverage.players=false` |
| `/standings` | `get_standings` / `sync_standings` | `league`, `season` | daily/explicit table refresh | optional | 12h | Blocked by `coverage.standings=false` |
| `/injuries` | `get_injuries` / `sync_injuries` | `league`, `season`, optional `fixture` | selected fixture, pre-match windows | optional | 3h | `reported` stays `reported`; empty responses cool down through cache |
| `/fixtures/lineups` | `get_lineups` / `sync_lineups` | `fixture` | selected fixture near kickoff | optional | 3h | No repeated polling after a cached empty response; status is not upgraded to official |
| `/fixtures/statistics` | `get_statistics` / `sync_statistics` | `fixture`, optional `team` | completed fixtures only | optional | long-lived | Unfinished matches are rejected; missing values are null |

## Request and quota review

* Every fresh response is saved in `raw_data_snapshots` with a normalized request hash and expiry. A cache hit returns the original snapshot timestamp and is marked `cached_provider_snapshot` in service logs; it does not increment provider usage.
* `httpx.Headers` is used case-insensitively for `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining`, `X-RateLimit-Limit` and `X-RateLimit-Remaining` (plus minute variants).
* Transport, 429 and 5xx retries are finite and use exponential backoff/`Retry-After`; each provider attempt remains subject to the quota gate. No retry can turn an exhausted quota into simulated data.
* The five target competitions share one database and one coverage cache keyed by competition and season. The service does not request lineups, injuries, players or statistics for unselected fixtures.

## Free-plan estimate

The conservative internal budget is 80 requests/day with a 20-request reserve. A typical selected match uses one cached fixture request plus, when coverage and remaining quota permit, one injuries request, one players request per team, one lineup request and one completed-statistics request: approximately 5–7 fresh calls per match. Therefore 1–3 carefully selected matches/day is the safe operating target; the exact allowance always follows live `/status` and response headers.

The API-Football `/predictions` endpoint is intentionally not used. If added in the future it may only be stored as an explicitly labelled `external_view`, never as a Sakura result, training label or official conclusion.
