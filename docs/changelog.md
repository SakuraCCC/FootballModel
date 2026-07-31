# Changelog

## V3.2 - Production Launch Preparation

- Added the non-blocking `production_check` CLI for environment, infrastructure, provider quota, storage, and five-competition readiness.
- Added release metadata (`model_version`, `feature_version`, `data_version`, `prompt_version`, and `poster_version`) to prediction, report, poster, and archive outputs without changing prediction algorithms.
- Added `prompt_experiments` and `daily_operation_reports` persistence, plus `/api/v1/dashboard/daily-report`.
- Extended the controlled E2E output with release/version and provider-usage fields. Missing live credentials remain `not_executed`.
- Updated the package and FastAPI release version to V3.2 and documented the first real production run in `docs/first-production-run.md`.

## Phase 11 - personal console, free-data modes, and production acceptance

- Added the API-Football endpoint audit, runtime plan/limit detection, case-insensitive rate-limit parsing, finite retry budgeting, coverage gates, and request-hash snapshot caching.
- Added `api_football`, `hybrid`, `manual`, and `offline` data modes with provenance-preserving CSV/JSON import APIs.
- Added quota/coverage/import/batch-export persistence, setup status, audit and first-run CLIs, and a protected personal dashboard.
- Added protected batch ZIP export with source manifests that exclude keys, environment files, and unnecessary raw responses.
- Fixed CI production Compose validation by creating a temporary `.env.production` fixture from the committed example and removing it after validation.
- Real provider and LLM E2E remains `not_executed` until the user supplies live credentials; no mock data was used.

## Phase 9 — Production Hardening & Model Optimization

- Added scheduler health with PostgreSQL, Redis, and Beat-heartbeat status; added explicit provider health and recent automation failure APIs.
- Added structured correlation IDs to JSON logs and persisted failure reason, failed step, and last retry timestamp for automation runs.
- Added source-preserving match statistics, player importance scoring storage, recent form trends, model provenance versions, reliability calibration, and prediction archives.
- Added a read-only lightweight operations dashboard at `/api/v1/dashboard/admin`; reports and PNG assets remain available through existing APIs, with no third-party publication automation.
- Added Phase 9 tests for scheduler health, provider status, automation failures, calibration, archive persistence, and unavailable player-input handling.
- Real production E2E is documented as pending because no local API-Football or LLM credential was configured; no mock was substituted.
- Added filtered model-performance analysis by competition, model name, and kickoff-date range.

## Phase 10 — Real ingestion, acceptance, and security hardening

- Added persistent standings, player-season statistics, injuries, lineups, provider quota usage, and real match-statistics/result synchronization APIs.
- Added API-Football timeout, finite 429/5xx retry with `Retry-After`, and raw snapshot/quota persistence.
- Added daily fixture/context sync, pre-match refresh, post-match result sync, duplicate-safe evaluation scheduling, and Beat entries.
- Added production admin-key authentication, CORS allowlist, rate limiting, secure response headers, and fail-closed production configuration.
- Added report/poster manual review state and approve/reject APIs; no platform auto-publishing was added.
- Added controlled E2E CLI, production smoke/restore scripts, CI Compose/build/Playwright checks, and documented the local no-credentials result.

## Phase 7 + Phase 8 MVP — 自动化运营与生产部署基础

- 新增未来 24–72 小时比赛扫描、Celery Beat 的每日扫描/生成/清理任务和可审计自动化流水线。
- 新增 `automation_runs`、内容资产查询、仪表盘汇总和模型表现 API。
- 新增生产 Docker Compose、Nginx、worker/beat、结构化日志、健康检查、备份脚本与部署文档。
- 自动化不会执行第三方账号登录或小红书自动发布；报告和 PNG 仍以 API/静态地址交付。

## Phase 6 — 比赛海报生成系统

- 新增五套赛事 HTML/CSS 模板、风格映射、固定水印与 Playwright PNG 渲染器。
- 新增 `poster_outputs`、`content_publish_records`、海报生成/查询 API 和静态图片地址。
- 只允许已审校的报告生成海报；文字来自结构化字段，不使用图片模型。
- 修复 CI 中 `tests.*` 共享测试辅助模块无法导入的问题，并加入 Chromium 安装步骤。

## Phase 5 — AI 报告生成与事实审校系统

- 新增来源保留的 `ReportContext`、内部报告与小红书报告生成服务。
- 新增文件化、版本化 Prompt 和 OpenAI 兼容 LLM Client；未配置时安全返回 `llm_unavailable`。
- 新增事实审校与高风险词风控，禁止将 `reported` 升级为确认事实。
- 新增 `report_outputs`、报告生成/查询 API，以及 Prompt、Schema、审校、风控和生成测试。

## Phase 4.5 — 历史回测与模型评估系统

- 扩展最终赛果存储，新增结果、总进球、BTTS 与完赛时间。
- 新增预测评价和按赛事聚合的模型表现表。
- 实现赛后评价服务：胜平负、精确比分、Top 3 比分、总进球区间、BTTS、Log Loss、Brier Score。
- 实现按开球时间回放的历史回测，并限制输入快照不得晚于开球时间。
- 新增赛果录入、执行评价、总体/赛事评价汇总与执行回测 API。
- 增加概率指标、评价服务和历史回测测试。

## Phase 4 — 预测模型与评分系统

- 实现 Feature Builder、Poisson、Dixon-Coles、Elo、综合模型、10,000 次比分模拟和置信度校准。
- 新增模型版本、模型运行与预测结果持久化及预测运行/查询 API。
- 数据不足时持久化 `not_available`，不产生虚构预测。

## Phase 3 — 数据接入层

- 实现 API-Football Adapter、统一 Provider 接口、标准化、来源追踪、原始响应快照和质量评分。
- 新增 API-Football 联赛与比赛同步 API，真实数据保留 `reported` certainty。

## Phase 2 — 分析任务闭环

- 建立 Analysis Job 生命周期、Celery 链、结构化管线测试结果及测试覆盖。

## Phase 1 — 项目基础设施

- 建立 FastAPI、PostgreSQL、Redis、Celery、Docker Compose、Alembic 与基础 API。
