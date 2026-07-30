# 数据库设计

## 核心表

`competitions`、`seasons`、`teams`、`players`、`matches`、`data_sources`、`raw_data_snapshots`、`analysis_jobs`、`analysis_job_matches`、`analysis_results`、`model_versions`、`model_runs`、`prediction_results`。

`competitions` 使用稳定代码：`CSL`、`MLS`、`LIGA_MX`、`UCL_QUALIFIER`、`BRA_SERIE_A`。规范化实体通过外键关联统一赛事维度。`data_sources` 保存供应商元数据；`raw_data_snapshots` 保存审计用原始响应。

## Phase 4.5 表与扩展

- `actual_results`：每场比赛唯一一条最终赛果，含 `match_id`、主客比分、`result`、`total_goals`、`btts_result`、`completed_at`、可选来源和备注。
- `prediction_evaluations`：每个 `prediction_id` 最多一条评估，关联 `actual_result_id`，保存五项布尔命中结果、`log_loss`、`brier_score` 与 `evaluated_at`。
- `model_performance`：以 `(model_version_id, competition_id)` 唯一，保存 `sample_count`、方向准确率、Log Loss、Brier Score 与计算时间。

`model_runs.prediction_id` 将一次预测关联到其 Poisson、Dixon-Coles、Elo 与 Ensemble 运行，支持逐模型表现统计。迁移只新增或兼容扩展，不破坏 Phase 1–4 的数据。

## Phase 5 报告输出

`report_outputs` 保存每次生成的报告：`prediction_id`、`report_type`（`internal` 或 `xiaohongshu`）、`content`、`prompt_version`、`llm_model` 与创建时间；另存储 `status` 和 `warnings`，用于表达 `generated`、`warning` 或 `llm_unavailable`。报告内容可为空，仅限 LLM 未配置或不可用的可恢复状态。

## 时间完整性

`model_runs.input_snapshot_id` 指向预测输入快照。回测时该快照的 `retrieved_at` 必须不晚于比赛 `kickoff_at`；最终赛果仅用于赛后评价。
