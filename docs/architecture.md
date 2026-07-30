# Sakura AI 足球预测系统 V2.0 架构

## 项目目标

系统长期提供可追溯的足球数据采集、标准化、分析、预测、报告与赛后复盘能力。GitHub 是唯一代码仓库；所有密钥仅通过环境变量提供。

## 当前阶段与边界

- Phase 1：FastAPI、PostgreSQL、Redis、Celery、Docker、基础 API。
- Phase 2：Analysis Job 生命周期和仅用于管线验证的结构化输出。
- Phase 3：真实数据供应商适配、标准化、来源与原始响应追踪、数据质量评分。

Phase 3 不实现预测模型、LLM、文章、海报或前端。任何 Phase 2 测试结果都必须保留 `mock_for_pipeline_test=true`，不得表现为真实预测。

## 分层

1. API 层只验证请求、调用服务并返回标准化响应。
2. `services/ingestion` 是第三方数据供应商的唯一入口；业务逻辑不得直接请求供应商 HTTP API。
3. `services/normalization` 将供应商对象映射到系统统一实体。
4. `services/quality` 评估数据完整度，不改变事实内容。
5. PostgreSQL 保存规范化实体、来源与原始响应快照；Celery 执行异步任务。

## 数据原则

- 全部赛事使用统一 `competition_id`，不按赛事分库或分表。
- 每一份外部数据必须关联来源、获取时间与 `certainty`。
- `official`、`confirmed`、`reported`、`predicted`、`unavailable` 不可混用；`reported` 不能升级为 `confirmed`。
- 无供应商字段一律保存为 `null` 或 `unavailable`，不以 mock 数据补全。
- 原始 HTTP 响应保存到 `raw_data_snapshots`，以便未来追溯分析和预测输入。

## 开发流程

每次开发先阅读本文件。后续 Phase 默认从当前分支继续；完成验证后提交并合并到 `main`。已完成 Phase 的核心行为只有在兼容性或数据正确性必要时才能修改。
