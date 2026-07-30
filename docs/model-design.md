# 模型设计

## Phase 4 预测管线

模型只使用已标准化、可追溯的比赛、赛果和数据快照。Feature Builder 产出近期胜平负、进失球、主客场表现、排名与积分（存在时）、休息天数和数据完整度。缺失数据保持 `null` 并降低置信度。

- Poisson：从真实历史进失球及联赛平均进球生成比分分布和胜平负概率。
- Dixon-Coles：对 Poisson 的低比分相关性做修正，版本为 `dixon_coles_v1`。
- Elo：按时间顺序从已保存赛果计算球队强度和主场调整。
- Ensemble：融合可用模型，输出方向、总进球区间、BTTS 和候选比分。
- Score Simulator：使用固定种子的 10,000 次模拟统计比分排名；分布过散时降低置信度。

若缺少必要历史数据，模型返回 `not_available`，不会虚构特征或预测。

## Phase 4.5 评估与回测

`actual_results` 保存最终比分。`prediction_evaluations` 将一个预测与一个真实赛果关联，并记录方向、精确比分、Top 3 比分、总进球区间、BTTS、Log Loss 和 Brier Score。

评价含义：

- 胜平负准确率：预测方向是否与赛果一致。
- 比分 Top 3 命中率：实际比分是否位于综合模型前三候选比分。
- 总进球区间与 BTTS 准确率：预测标签是否与实际赛果一致。
- Log Loss：真实结果对应概率的负对数，越低越好。
- Brier Score：三分类概率与真实 one-hot 结果的均方误差，越低越好。

回测按开球时间升序重放历史比赛，并由 Feature Builder 强制使用开球前快照。每次运行创建可审计的 `model_runs`、`prediction_results` 和评价记录；`model_performance` 按模型版本和赛事汇总表现。

## Phase 5 报告与事实审校

`ReportContext` 聚合比赛信息、已确认事实、来源报道、模型预测、比分复核、风险、完整度、置信度、输入快照和可选评价结果。报告不修改任何预测模型或预测结果。

内部报告要求包含数据截止时间、来源说明、数据完整度、双方分析、模型结果、比分复核和风险说明。小红书版本限制在 1,000 字以内，必须包含比赛、时间、核心差异、模型方向、三个比分、风险与固定免责声明。

Prompt 以文件方式管理：`internal_report_v2.md`、`xiaohongshu_v2.md`、`fact_review_v2.md`。事实审校拒绝将 `reported` 表述为确认事实；内容风控对“投注、收益、稳赚、串关、梭哈”等高风险词返回 `warning`。

## Phase 6 海报渲染

海报不是预测模型，也不使用 AI 图片生成。`PosterService` 只接受 `status=generated` 的报告，读取其预测的联赛、北京时间、球队、方向、总进球范围、BTTS、三组比分、风险等级和置信度。五个赛事代码映射到独立 HTML/CSS 模板，Playwright Chromium 在固定 1080×1350 画布截图为 PNG；水印固定为 `Sakura Football Model V2.0`。

## Phase 7–8 自动化与交付

Celery Beat 每日依次调度比赛扫描、自动分析生成与临时文件清理。自动链路创建审计用 Analysis Job，再执行既有预测、已审校报告和固定模板海报服务；模型、评分和事实审校逻辑不在自动化中改写。

报告文字可通过报告 API 返回并复制，海报通过静态 PNG URL 返回。系统不代替用户登录、发布或操作小红书等外部平台。

## Phase 9 特征、校准与版本复盘

Feature Builder 在已有最近五场赛果基础上增加进球、失球、射门和 xG 的每场趋势。射门和 xG 仅来自 `match_statistics`；无至少两条真实观测时趋势为 `null`，并写入缺失字段。

`player_importance_scores` 的透明评分使用分钟、进球、助攻与位置权重；它是伤停影响可用前的事实基础，不能用臆测数据驱动模型。

`confidence_calibration` 将已赛后评估的模型概率按 0.1 区间聚合，保存观测频率、Calibration Error 和 Reliability（`1 - error`）。各预测 model run 同时保存 `feature_version`、`data_version`、`prompt_version`、`calibration_version`，因此可按赛事、模型和版本回放表现。

`prediction_archive` 固化输入摘要、模型输出、可用报告、海报路径及赛后结果，是未来训练新版本前的审计素材，不反向污染历史模型输入。

`GET /api/v1/evaluation/model-performance` 可按 `competition_code`、`model_name`、`start_date` 和 `end_date` 筛选已评估模型表现；时间筛选以比赛开球时间为准。
