# Changelog

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
