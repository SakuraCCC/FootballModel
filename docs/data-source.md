# 数据源设计

## 供应商接口

所有供应商实现 `BaseProvider`：`get_competitions`、`get_matches`、`get_team`、`get_players`、`get_lineups`、`get_injuries`、`get_statistics`。调用方只依赖该接口和规范化对象。

## API-Football

首个供应商为 API-Football。配置 `API_FOOTBALL_KEY` 后，服务使用 `x-apisports-key` 请求头访问其 v3 接口。密钥不能出现在代码、日志、文档示例或数据库快照中。

Phase 3 仅采集联赛、球队与比赛基础字段。未提供的字段保存为 `null`，不会模拟伤停、首发、球员或统计数据。

可用 API：

- `POST /api/v1/ingestion/api-football/competitions`：读取真实联赛配置，并为五项目标赛事更新 API-Football 联赛映射。
- `POST /api/v1/ingestion/api-football/matches`：读取并保存指定赛事、赛季和可选比赛日期的真实赛程。

## 可追溯性

每一次供应商 HTTP 成功响应创建 `raw_data_snapshots` 记录：供应商、端点、请求时间、响应 JSON、检索时间与关联 `data_source_id`。来源记录明确供应商版本和 tier。
