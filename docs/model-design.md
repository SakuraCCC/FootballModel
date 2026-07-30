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
