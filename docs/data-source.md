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
