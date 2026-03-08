# GitHub 图表组件合并记录

## 操作日期
2026-03-08

## 背景
- GitHub 仓库: https://github.com/hahahachaoge/OilRisk_Alert-main
- 负责人: 黄彪骐（数据可视化工程师）
- 本地仓库为主干版本，GitHub 为分支交付

---

## 第一阶段：新增组件文件

### 新增文件（3个组件 + 1个导出文件）
1. `frontend/src/components/charts/PriceRiskAlertChart.vue` — 综合图表（油价+风险+预警）
   - 相比本地 PriceRiskChart 增强：预警按级别分3个scatter系列、自定义HTML tooltip、DataZoom支持、点击预警交互
   - 使用本地已有的 i18n key（`risk.level.Low/Medium/High`）
2. `frontend/src/components/charts/WeightAreaChart.vue` — 因子权重堆叠面积图
   - 本地原本缺失的交付物
   - 修复：分类命名使用 `t('factor.category.Supply-Demand')` 格式（与本地 i18n 一致）
3. `frontend/src/components/charts/AlertTimeline.vue` — 预警时间线
   - 本地原本缺失的交付物
   - 修复 bug：symbolSize 从箭头函数改为直接数值（ECharts 兼容性）
   - 修复 bug：i18n key 从 `alert.level.*` 改为 `risk.level.*`（与本地一致）
4. `frontend/src/components/charts/index.ts` — barrel export 统一导出

### 修改文件（i18n 补充）
- `frontend/src/i18n/zh-CN.ts` — 新增 `factorAnalysis.weightPercentage`、`weightHistory`
- `frontend/src/i18n/en-US.ts` — 同上英文版

---

## 第二阶段：集成到页面视图

### RiskOverview.vue 改动
1. **替换主图表**：`PriceRiskChart` → `PriceRiskAlertChart`
   - Props 接口完全兼容（dates, oilPrice, riskIndex, alerts）
   - 新增 `@select-alert="onAlertSelect"` 事件绑定
2. **新增 `onAlertSelect` 函数**和 `selectedAlert` ref（预留后续跳转逻辑）
3. **修复已有 bug**：RadarChart 缺少 `locale` prop
   - 新增 `useAppStore` 导入和 `locale` computed
   - RadarChart 标签添加 `:locale="locale"`
4. **新增 i18n key**：`overview.alertTimeline.title`（中：预警时间线 / 英：Alert Timeline）

> **注意**：最初同时添加了 `AlertTimeline` 组件到此页面，后发现与 `PriceRiskAlertChart` 功能重叠
> （PriceRiskAlertChart 已包含油价+风险指数+预警散点三合一），导致页面出现两个风险指数图。
> 已移除 AlertTimeline 的页面引用，仅保留 PriceRiskAlertChart。
> AlertTimeline 组件文件仍保留在 `charts/` 目录中，供其他页面独立使用。

### FactorAnalysis.vue 改动
1. **新增权重演变图区域**：在雷达图和底部之间插入 `WeightAreaChart`
   - 导入 `WeightAreaChart` 组件及其 `WeightDataPoint` 类型
2. **添加 mock 数据生成**：`generateMockWeightData()` 生成24个月的模拟权重数据
   - 后续可替换为真实API（TODO）
3. **CSS 新增** `.factor-analysis__weight-history` 样式（min-height: 380px）

### 未修改的文件
- `PriceRiskChart.vue` — 保留，未删除（旧版仍可用）
- `FactorShapChart.vue` — 保留本地版
- `RadarChart.vue` — 保留本地版（仅在 RiskOverview 补了 locale prop）
- 所有后端 Java/Python 文件 — 零改动

---

## 未采纳的内容及原因
| 内容 | 原因 |
|------|------|
| GitHub 版 RadarChart.vue | 本地版 tooltip 信息量更大（Top-3 SHAP因子），且已兼容后端 SUPPLY_DEMAND 格式 |
| GitHub 版 FactorShapChart.vue | 两版几乎一致，本地微调更好 |
| useChart.ts composable | 半成品，图表组件实际未使用它 |
| 单元测试 (__tests__/) | 测试的是独立 mock 函数非实际组件，且 jest/vitest 混用 |

---

## 兼容性注意事项
- **分类命名规范**：本地后端使用 `SUPPLY_DEMAND` 格式，前端 i18n key 使用 `Supply-Demand`。新组件统一走 `t('factor.category.Supply-Demand')` 路径
- **PriceRiskChart.vue 未删除**：旧版保留在 charts 目录，barrel export 中也保留导出
- **WeightAreaChart 数据为 mock**：`FactorAnalysis.vue` 中的 `generateMockWeightData()` 是临时数据，后续需要对接真实 API

---

## 验证结果
- `vue-tsc --noEmit`：零错误（修复了已有的 RadarChart locale prop 缺失）
- `vite build`：构建成功（11.64s），无报错
- GitHub 克隆目录 `OilRisk_Alert-main_github` 已删除

---

## TODO
- [ ] WeightAreaChart 对接真实权重历史 API（替换 mock 数据）
- [ ] `onAlertSelect` 实现跳转预警详情逻辑
- [ ] 考虑删除旧版 `PriceRiskChart.vue`（确认无其他引用后）
