# 数据库设计

核心实体：`competitions`、`seasons`、`teams`、`players`、`matches`、`data_sources`、`raw_data_snapshots`、`analysis_jobs`、`analysis_job_matches`、`analysis_results`、`model_versions`、`model_runs`、`prediction_results`。

`competitions` 用稳定代码区分 CSL、MLS、LIGA_MX、UCL_QUALIFIER、BRA_SERIE_A。所有规范化实体由外键关联该统一赛事维度。`data_sources` 保存供应商元数据；`raw_data_snapshots` 保存原始可审计响应。事实字段的 `certainty` 使用受限枚举值。

Phase 3 为 `competitions` 保存 API-Football 联赛映射；为赛季、球队、球员和比赛保存来源、供应商外部标识与 `certainty`。`matches` 的供应商缺失字段允许为 `null`，从而避免以假数据填充。

Phase 3 迁移只能新增或兼容扩展，不得破坏 Phase 1/2 表和数据。

Phase 4 的 `model_versions` 定义模型与版本；`model_runs` 关联比赛、模型版本和输入快照，并保存完整输出；`prediction_results` 保存综合方向、进球区间、BTTS、三轮比分复核和置信度。
