# Sakura AI 足球预测系统 V2.0 架构

## 项目目标

系统提供可追溯的足球数据采集、标准化、分析任务、预测、赛后评估与历史回测能力。GitHub 是代码唯一来源；密钥只通过环境变量提供。

## 当前阶段

- Phase 1：FastAPI、PostgreSQL、Redis、Celery、Docker、基础 API。
- Phase 2：Analysis Job 生命周期、异步任务链与仅用于管线验证的 mock 结构化结果。
- Phase 3：API-Football Provider、标准化、数据来源追踪、原始快照和数据质量评分。
- Phase 4：基于已保存数据的 Feature Builder、Poisson、Dixon-Coles、Elo、Ensemble、比分模拟和预测结果。
- Phase 4.5：真实赛果、赛后评估、模型表现聚合和无未来数据泄漏的历史回测。
- Phase 5：来源保留的报告上下文、外置版本化 Prompt、OpenAI 兼容 LLM、事实审校、内容风控与报告持久化。

Phase 5 不实现海报或前端。Phase 2 的 mock 输出必须始终带有 `mock_for_pipeline_test=true`，不得表现为真实预测。

## 分层

1. API 层验证请求、调用服务并返回标准化响应。
2. `services/ingestion` 是第三方数据源的唯一入口；业务代码不得直接调用供应商 HTTP API。
3. `services/normalization` 将供应商对象映射为统一实体；`services/quality` 只评价完整度，不改写事实。
4. `services/prediction` 只读取已保存的比赛、球队、赛果和快照，持久化模型运行与预测结果。
5. `services/evaluation` 根据最终赛果计算单次预测评价与按赛事聚合的模型表现。
6. `services/backtest` 按开球时间回放已完赛比赛；每次运行只能读取 `retrieved_at <= kickoff_at` 的快照。
7. `services/reporting` 只消费已保存的预测、模型运行、来源快照与评价结果；它将事实、报道和模型推断分开处理。

## 数据与时间原则

- 全部赛事共用统一 `competition_id`，不按赛事分库或分表。
- 外部事实必须关联来源、获取时间与 `certainty`。`reported` 不得提升为 `confirmed`。
- 供应商缺失字段使用 `null` 或 `unavailable`，禁止补造数据。
- 原始 HTTP 响应保存至 `raw_data_snapshots`，以支持输入追溯。
- 预测数据不足时返回 `not_available` 并保留原因。
- 回测绝不使用开球后的赛果、统计或快照；未来数据不可用于历史预测。
- 报告必须保留来源快照引用和 certainty；`reported` 不得转写为 `confirmed` 或官方信息。
- 未配置 LLM 时，报告 API 返回并持久化 `llm_unavailable`，不调用外部服务也不使请求失败。

## 开发流程

每次开发前先阅读本文件。后续 Phase 直接在当前 `main` 基础上开发；验证通过后提交并推送 `main`。已完成阶段的核心行为仅在兼容性或数据正确性必要时修改。
