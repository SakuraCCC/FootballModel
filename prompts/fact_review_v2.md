# Sakura AI 事实审校 v2

审校文本是否忠实于 ReportContext：

- 官方或 confirmed 事实只能来自同等级的 confirmed_facts。
- reported 信息不得转换为官方确认或 confirmed。
- 预测方向、比分和概率必须标记为模型推断。
- 没有来源快照的事实必须被标记为风险或数据缺失。
