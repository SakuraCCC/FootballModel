# 数据源设计

## Provider 接口

所有供应商实现 `BaseProvider`：`get_competitions`、`get_matches`、`get_team`、`get_players`、`get_lineups`、`get_injuries`、`get_statistics`。调用方只依赖统一接口和规范化对象。

## API-Football

首个供应商为 API-Football v3。配置 `API_FOOTBALL_KEY` 后，通过 `x-apisports-key` 请求头访问。密钥不得出现在代码、日志、文档示例或数据库快照中。

当前真实采集范围为联赛、球队和比赛基础信息。未提供的字段保存为 `null`，不模拟伤停、首发、球员或统计数据。

可用接口：

- `POST /api/v1/ingestion/api-football/competitions`
- `POST /api/v1/ingestion/api-football/matches`

## 可追溯性与回测

每次供应商成功响应都保存 `raw_data_snapshots`：供应商、端点、请求时间、响应 JSON、检索时间与 `data_source_id`。历史回测仅选择开球时刻或之前取得的快照；比赛结束后取得的资料不能参与该场预测。

最终赛果通过 `POST /api/v1/results` 保存，并可关联结果来源。赛果是评估目标，不是对应比赛预测特征的输入。

## 报告中的来源使用

Phase 5 的 `ReportContext` 从与预测关联的 `model_runs.input_snapshot_id` 读取快照，输出快照 ID、供应商、端点和检索时间。比赛的 `certainty` 决定其进入 `confirmed_facts` 或 `reported_information`；报告生成与事实审校均不得提升可信等级。

Phase 6 海报不再读取供应商 API，也不生成或修改事实。它只读取已审校报告对应的结构化预测字段，因此可通过 `report_id` 与 `prediction_id` 回溯其来源。

## 自动化扫描

Phase 7 仅扫描已由数据接入层保存、且开球时间在未来 24–72 小时内的比赛。扫描器不直接调用第三方 API；失败重试也只重用已入库数据和来源快照。已完成或正在执行的自动化记录不会重复入队。

## Phase 9 数据质量与供应商健康

`match_statistics` 按 `(match_id, team_id)` 保存比赛级统计：`shots`、`shots_on_target`、`possession`、`corners`、`xg`、`xga` 与来源快照。任何 API 未提供的字段均为 `null`，并以 `certainty=unavailable` 表达，禁止估算或补全。

`GET /api/v1/providers/status` 返回供应商可访问性、响应时间、最近快照时间和最近比赛字段完整度。未设置 `API_FOOTBALL_KEY` 会返回 `unavailable`；该状态不是“健康”，也不会消耗 API 配额。

球员影响评分只接受已获取的分钟、进球、助攻及位置。没有分钟数据时评分为 `null`，伤停影响在缺少可追溯球员数据时不会进入预测。
