# OilRisk-Alert 项目结构与技术指南

> 供后续开发智能体快速理解项目全貌的参考文档。最后更新：2026-03-06

---

## 一、项目概述

**OilRisk-Alert** 是一个原油价格风险预警系统，采用多模型集成（LSTM + XGBoost + Stacking）进行 5 个交易日的 WTI 原油价格风险预测，并通过 Web 界面展示风险仪表盘、因子分析、预警记录和模型回测。

### 整体架构

```
Vue 3 前端 (5173)  ──/api 代理──▶  Spring Boot 后端 (8080)  ──HTTP──▶  FastAPI 推理引擎 (5000)
                                         │                                    │
                                    MySQL 8.0 (3306)                   ML 模型文件 + CSV 数据
```

| 组件 | 技术栈 | 端口 | 职责 |
|------|--------|------|------|
| 前端 | Vue 3 + Vite + TypeScript + ECharts | 5173 | 用户界面、可视化 |
| 后端 | Spring Boot 4.0 + MyBatis + MySQL | 8080 | REST API、业务逻辑、LLM 报告生成 |
| 推理引擎 | FastAPI + PyTorch + XGBoost | 5000 | 模型推理、回测 |
| 数据库 | MySQL 8.0 | 3306 | 持久化（风险指数、预警、因子） |

---

## 二、目录结构

```
OilRisk_Alert/
├── src/main/java/com/example/oilrisk_alert/   # Java 后端
│   ├── OilRiskAlertApplication.java            # 启动类
│   ├── common/                                 # 通用：Result、BusinessException、GlobalExceptionHandler、RiskLevel
│   ├── config/                                 # 配置：CORS、RestTemplate、WeightsConfig、LlmConfig
│   ├── controller/                             # 控制器（6 个）
│   ├── service/ + service/impl/                # 服务层（6 对接口+实现）
│   ├── mapper/                                 # MyBatis Mapper 接口（3 个）
│   ├── entity/                                 # 实体类（3 个）
│   ├── dto/                                    # 请求 DTO（4 个）
│   ├── vo/                                     # 响应 VO（12+ 个）
│   └── util/                                   # LttbUtil（时序降采样）
├── src/main/resources/
│   ├── application.properties                  # 后端配置
│   ├── schema.sql                              # 建表脚本
│   └── mapper/*.xml                            # MyBatis XML（3 个）
├── frontend/                                   # Vue 前端
│   ├── src/
│   │   ├── api/                                # Axios 请求层（7 个模块）
│   │   ├── views/                              # 页面（4 个）
│   │   ├── components/layout/                  # 布局：AppLayout、SideBar、TopBar
│   │   ├── components/charts/                  # 图表：RiskGauge、RadarChart、PriceRiskChart 等（5 个）
│   │   ├── components/common/                  # 通用：LlmConfigModal、AlertCard
│   │   ├── composables/                        # 组合式函数（4 个）
│   │   ├── stores/                             # Pinia 状态（app、risk）
│   │   ├── types/                              # TypeScript 类型定义（4 个）
│   │   ├── i18n/                               # 国际化（中文/英文）
│   │   ├── theme/                              # ECharts 主题（dark/light）
│   │   └── router/                             # Vue Router（4 条路由）
│   ├── vite.config.ts
│   └── package.json
├── OilRisk_System/                             # ML 训练脚本 + 模型文件 + 数据
│   ├── LSTM.py                                 # LSTM 趋势专家
│   ├── Xgboost_model1.py                       # XGBoost 冲击专家
│   ├── stacking最终.py                          # Stacking 元学习器
│   ├── OilRisk_Engine.py                       # 统一推理引擎
│   ├── Final_Oil_Dataset_Cleaned.csv           # 原始数据（400+ 列 × 6000+ 行）
│   ├── best_lstm.pt                            # LSTM 模型权重
│   ├── xgb_wti_shock_model.pkl                 # XGBoost 模型
│   ├── meta_ridge_model.pkl                    # Ridge 元学习器
│   ├── feat_scaler.pkl / price_scaler.pkl      # RobustScaler
│   └── feature_cols.pkl                        # LSTM 特征列名
├── python_engine/                              # FastAPI 推理服务
│   ├── app.py                                  # FastAPI 入口
│   ├── engine.py                               # OilRiskEngine 类
│   └── requirements.txt                        # Python 依赖
├── data/Final_Oil_Dataset_Cleaned.csv          # 数据副本
├── md/                                         # 启动指南、团队工作总结
├── doc/                                        # 设计文档、需求文档
└── pom.xml                                     # Maven 配置
```

---

## 三、后端 API 接口清单

### 风险数据

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| GET | `/api/risk/current` | 当前风险指数 + Top 5 因子 | `RiskCurrentVO` |
| GET | `/api/factors/timeseries?start=&end=` | 时序数据（油价、风险、预警标记） | `TimeseriesVO` |
| POST | `/api/predict/daily` | 触发 Python 引擎日预测 | `Map<String, Object>` |
| GET | `/api/risk/signals` | 三模型信号（LSTM/XGBoost/Stacking） | `ModelSignalVO` |

### 预警管理

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| GET | `/api/alerts?page=&size=&level=&sort=&order=` | 分页预警列表 | `PageVO<AlertVO>` |
| GET | `/api/alerts/{id}` | 预警详情 + 触发规则 | `AlertDetailVO` |

### 因子分析

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| GET | `/api/risk/radar?date=` | 雷达图数据（5 类因子评分） | `List<RadarScoreVO>` |
| GET | `/api/explain/{date}` | 指定日期因子 SHAP 贡献 | `List<FactorVO>` |
| PUT | `/api/config/weights` | 更新因子类别权重 | `WeightUpdateResultVO` |

### AI 报告

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| GET | `/api/report/{alertId}` | 流式 AI 报告（SSE） | `SseEmitter` |
| GET | `/api/risk/ai-summary` | 流式 AI 风险摘要（SSE） | `SseEmitter` |

### 模型回测

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| POST | `/api/predict/backtest` | 回测请求（转发 Python 引擎） | `BacktestResultVO` |

### LLM 配置

| 方法 | 路径 | 说明 | 返回类型 |
|------|------|------|----------|
| GET | `/api/config/llm` | 获取 LLM 配置（Key 脱敏） | `LlmConfigVO` |
| PUT | `/api/config/llm` | 更新 LLM 配置 | `LlmConfigVO` |

---

## 四、数据库表结构

```sql
-- 每日风险指数
risk_index (
  id BIGINT PK AUTO_INCREMENT,
  date DATE NOT NULL UNIQUE,
  risk_index DECIMAL(5,2),          -- 0-100
  risk_level VARCHAR(20),           -- Low / Medium / High
  oil_price DECIMAL(10,2),
  created_at TIMESTAMP
)

-- 预警记录
alert (
  id BIGINT PK AUTO_INCREMENT,
  date DATE NOT NULL,
  level VARCHAR(20),                -- Low / Medium / High
  risk_index DECIMAL(5,2),
  trigger_type VARCHAR(100),
  trigger_factor VARCHAR(255),      -- 英文因子名
  trigger_factor_zh VARCHAR(255),   -- 中文因子名
  summary TEXT,
  summary_en TEXT,
  detail JSON,                      -- 触发规则 JSON
  ai_report TEXT,                   -- LLM 报告缓存
  created_at TIMESTAMP
)

-- 风险因子（SHAP）
risk_factor (
  id BIGINT PK AUTO_INCREMENT,
  date DATE NOT NULL,
  factor_name VARCHAR(255),
  factor_name_zh VARCHAR(255),
  category VARCHAR(50),             -- SUPPLY_DEMAND / MACRO / FINANCIAL / GEOPOLITICAL / SENTIMENT
  value DECIMAL(20,4),
  shap_value DECIMAL(20,4),
  created_at TIMESTAMP
)
```

数据库配置：MySQL 8.0，`localhost:3306/oilrisk`，用户 `root`，密码 `123456`。

---

## 五、ML 模型体系

### 三专家集成架构

```
原始数据 (CSV 400+列)
    │
    ├──▶ LSTM 趋势专家
    │     输入: 27 特征 × 30 日窗口
    │     输出: pred_price, up_prob, direction
    │
    ├──▶ XGBoost 冲击专家
    │     输入: ~40-50 风险相关特征
    │     输出: risk_score (下行风险幅度)
    │
    └──▶ Stacking 元学习器 (Ridge)
          输入: 7 市场状态 + LSTM隐含收益率 + XGB风险值
          输出: pred_return_pct → 风险评分 (0-100)
```

### LSTM 趋势专家

- **架构**: 双头 LSTM（价格回归 + 方向分类）
- **层**: 2 层 LSTM [128, 64] + BatchNorm + Dropout(0.2)
- **损失**: Huber Loss + 0.5 × BCE
- **窗口**: lookback=30 天, horizon=5 天
- **特征 (27)**:
  - 价格自身：WTI 收盘价
  - 金融日频(7)：CRB、SP500、TIPS、HY Spread、VIX、OVX、库欣库存
  - 月度变化(6)：OPEC/沙特/俄罗斯产量、中国/欧盟 PMI、美国情绪
  - 技术指标(8)：MA5/20/60、偏离度、动量、历史波动率
  - 方向性(3)：动量加速度、VIX/OVX 3日变化
- **输出**: `lstm_pred_price`, `lstm_up_prob`, `lstm_direction`

### XGBoost 冲击专家

- **目标**: `risk = max(0, -5日收益率)` — 仅关注下行风险
- **参数**: n_estimators=600, max_depth=4, lr=0.03, subsample=0.8
- **特征**: 通过关键词（ovx, vix, spread, risk, sentiment 等）筛选 ~40-50 列
- **评估**: TimeSeriesSplit 5 折, Spearman 相关, Top10% Lift
- **输出**: `xgb_risk_score`

### Stacking 元学习器

- **模型**: Ridge 回归 (L2 正则化)
- **输入 (9 维)**:
  - 市场状态(7): VIX, OVX, 10Y 收益率, 美元指数, 新闻情绪, 地缘分数, SP500
  - LSTM 隐含收益率(1): `(pred_price - current_price) / current_price`
  - XGBoost 风险值(1): `xgb_risk_score`
- **输出**: `pred_return_pct`（5 日预测收益率 %）
- **风险评分转换**: `score = clamp(50 - pred_return_pct × 10, 0, 100)`
- **风险区间**: ≤25 分位 → 高风险, 25-75 分位 → 中风险, ≥75 分位 → 低风险

### Python 推理引擎接口

```
GET  /health                → {"status":"ok", "models_loaded": true}
POST /predict/daily         → 日预测 JSON（dashboard + expert_signals + top_factors + prediction）
POST /predict/backtest      → 回测结果（dates, actual, predicted, metrics）
```

**日预测输出示例**:
```json
{
  "status": "success",
  "dashboard": { "score": 45.25, "level": "低风险" },
  "expert_signals": {
    "lstm_impl_return": "-4.91%",
    "lstm_direction": "下跌↓",
    "xgb_risk_score": 0.00277
  },
  "top_factors": [
    {"name": "VIX_Index", "value": 156.23}, ...
  ],
  "prediction": { "predicted_return_pct": 0.137 }
}
```

---

## 六、前端页面与核心组件

### 路由 (4 页)

| 路径 | 视图 | 功能 |
|------|------|------|
| `/` | `RiskOverview.vue` | 仪表盘：风险仪表、雷达图、价格趋势、预警卡片、AI 摘要、模型信号 |
| `/factors` | `FactorAnalysis.vue` | 因子分析：雷达图、SHAP 条形图、权重调节滑块 |
| `/alerts` | `AlertRecords.vue` | 预警记录：分页表格、级别筛选、触发规则展开、AI 报告流式生成 |
| `/backtest` | `ModelBacktest.vue` | 模型回测：日期范围选择、模型切换、多模型叠加对比图、准确率指标 |

### 图表组件 (ECharts 5.6)

| 组件 | 类型 | 用途 |
|------|------|------|
| `RiskGauge.vue` | 仪表盘 | 0-100 风险评分，颜色随级别变化 |
| `RadarChart.vue` | 雷达图 | 5 类因子（供需/宏观/金融/地缘/情绪）评分 |
| `PriceRiskChart.vue` | 双轴折线 | 油价 + 风险指数趋势，含预警标记 |
| `FactorBarChart.vue` | 水平条形 | Top 5 因子 SHAP 贡献 |
| `FactorShapChart.vue` | 水平条形 | Top 10 因子 SHAP（正负双色） |

### 状态管理 (Pinia)

- **app store**: theme（dark/light）、locale（zh-CN/en-US）、timeRange、sidebarCollapsed
- **risk store**: currentRisk、timeseriesData、loading、error、stale

### 关键特性

- **流式 AI 报告**: EventSource 接收 SSE 流，逐 token 展示（打字机效果）
- **国际化**: vue-i18n 支持中英文切换
- **暗色/亮色主题**: CSS 变量 + ECharts 主题配置
- **时间范围预设**: 1y / 2y / 5y / all 快捷按钮
- **LTTB 降采样**: 后端对 >2000 点的时序数据自动降采样
- **LLM 配置**: 前端弹窗可修改 API Key / URL / 模型名

---

## 七、核心业务逻辑

### 风险评分计算

1. Python 引擎运行三模型推理 → 输出 `pred_return_pct`
2. 转换公式: `score = clamp(50 - pred_return_pct × 10, 0, 100)`
3. 风险级别: Low [0,40) / Medium [40,70) / High [70,100]

### 因子评分（雷达图）

1. 按 5 个类别分组因子，计算各类别平均 |SHAP|
2. 乘以类别权重（默认 1.0，可调 0-2）
3. 归一化到 0-100

### 权重调节

1. 用户拖动滑块设置 5 类权重（0-2）
2. 重算公式: `adjustedIndex = originalIndex × (加权SHAP总和 / 无权SHAP总和)`
3. 实时更新雷达图和风险指数

### AI 报告生成

1. 检查 `alert.ai_report` 缓存 → 有则直接流式返回
2. 无缓存且无 API Key → 返回 Mock 模板
3. 有 API Key → 调用 LLM（iFlow/Qwen）流式生成 → 缓存到数据库

### 时序数据流

```
前端请求 → 后端查 risk_index + alert 表 → LTTB 降采样（>2000点时） → 返回 TimeseriesVO
```

---

## 八、关键配置

### 后端 application.properties

```properties
server.port=8080
spring.datasource.url=jdbc:mysql://localhost:3306/oilrisk?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
spring.datasource.username=root
spring.datasource.password=123456
python.engine.url=http://localhost:5000
llm.api.url=https://apis.iflow.cn/v1/chat/completions
llm.api.model=qwen3-max
```

### 前端 vite.config.ts

```typescript
server: {
  port: 5173,
  proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } }
}
```

### Python requirements.txt

```
fastapi>=0.115.0, uvicorn>=0.30.0, pandas>=2.2.0, numpy>=1.26.0,
scikit-learn>=1.5.0, torch>=2.5.0, xgboost>=2.1.0, shap>=0.46.0, joblib>=1.4.0
```

---

## 九、启动顺序

**必须按此顺序启动：**

1. **MySQL** — 确保 `oilrisk` 数据库存在
2. **Python 推理引擎 (5000)** — `cd python_engine && uvicorn app:app --host 0.0.0.0 --port 5000`
3. **Spring Boot 后端 (8080)** — `mvnw spring-boot:run` 或 IDE 运行
4. **前端开发服务器 (5173)** — `cd frontend && npm install && npm run dev`

---

## 十、重要技术决策与注意事项

1. **数据不泄漏**: ML 训练严格按时间序列切分（70/15/15），不 shuffle
2. **RobustScaler**: LSTM 使用 RobustScaler 对价格和特征归一化，抗异常值
3. **XGBoost 不前向填充**: 保持训练一致性，仅元学习器的市场状态特征前向填充
4. **LTTB 降采样**: 保留视觉特征同时将点数降到 2000 以内
5. **AI 报告缓存**: 生成后存入 `alert.ai_report` 字段，避免重复调用 LLM
6. **SQL 注入防护**: 后端对 sort/order/level 参数做白名单校验
7. **Spring Boot 4.0**: 项目使用 Spring Boot 4.0.3（注意与传统 2.x/3.x 的差异）
8. **双头 LSTM**: 同时输出价格预测和方向概率，通过加权损失联合训练
9. **LLM 可选**: 无 API Key 时回退到 Mock 模板，不影响核心功能

---

## 十一、已实现功能清单

- [x] 风险仪表盘（实时评分 0-100、级别指示、Top 5 因子）
- [x] 双轴时序图（油价 + 风险指数 + 预警标记）
- [x] 因子雷达图（5 类因子评分、权重可调）
- [x] SHAP 因子贡献可视化
- [x] 预警记录管理（分页、筛选、排序、触发规则详情）
- [x] AI 报告生成（LLM 流式输出、缓存机制）
- [x] 模型回测（3 模型、多模型叠加对比、准确率指标）
- [x] 三模型信号面板（LSTM/XGBoost/Stacking 各自输出）
- [x] 中英文国际化
- [x] 暗色/亮色主题切换
- [x] LLM 配置管理
