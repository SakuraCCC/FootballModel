# Changelog

## Phase 4 — 预测模型与评分系统

- 实现基于已保存比赛、赛果和快照的 Feature Builder。
- 实现 Poisson、Dixon-Coles、Elo、综合模型、10,000 次比分模拟与置信度校准。
- 新增模型版本、模型运行、预测结果表以及预测运行/查询 API。
- 数据不足时持久化 `not_available`，不产生虚构预测。

## Phase 3 — 数据接入层

- 实现 API-Football Adapter、统一供应商接口、标准化、来源追踪、原始响应快照和质量评分。
- 新增 API-Football 联赛与比赛同步 API，所有真实数据保留 `reported` certainty。

## Phase 2 — 分析任务闭环

- 建立 Analysis Job 生命周期、Celery 链、结构化管线测试结果及测试覆盖。

## Phase 1 — 项目基础设施

- 建立 FastAPI、PostgreSQL、Redis、Celery、Docker Compose、Alembic 与基础 API。
