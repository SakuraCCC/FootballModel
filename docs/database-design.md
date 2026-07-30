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

## Phase 6 海报与运营基础

- `poster_outputs`：关联 `report_id` 与 `prediction_id`，保存 `competition_style`、PNG `file_path`、`template_version` 和创建时间。
- `content_publish_records`：为 Phase 7 预留发布记录，保存报告、可选海报、平台、发布时间、浏览、点赞、收藏和评论。

海报只允许关联通过审校的 `report_outputs`，不会写回或改变预测、报告事实和模型输出。

## Phase 7 自动化运行

`automation_runs` 以 `match_id` 唯一，关联自动创建的 Analysis Job、预测、报告和海报，并保存 `status`、`current_step`、`error_message`、`retry_count` 与 Celery `task_id`。该表使自动链路的失败与重试可追踪，而 `content_publish_records` 继续用于人工发布状态及未来运营分析。

## 时间完整性

`model_runs.input_snapshot_id` 指向预测输入快照。回测时该快照的 `retrieved_at` 必须不晚于比赛 `kickoff_at`；最终赛果仅用于赛后评价。

## Phase 9 表与字段

- `match_statistics`：每场、每队真实统计及其 certainty/source snapshot；字段缺失保存 `NULL`。
- `player_importance_scores`：球员分钟、进球、助攻、位置、位置权重和透明影响分数；缺少原始统计时 score 为 `NULL`。
- `scheduler_heartbeats`：每个 Beat 任务最近执行时间和 Celery task ID，用于 scheduler health。
- `confidence_calibration`：模型版本、赛事、概率桶、样本量、观测频率、校准误差、可靠性和计算时间。
- `prediction_archive`：每个 prediction 唯一的输入摘要、模型输出、报告正文、海报路径、赛后结果及归档时间。
- `automation_runs` 新增 `failure_reason`、`failed_step`、`last_retry_time`；`model_versions` 和 `model_runs` 新增 feature/data/prompt/calibration 版本维度。
