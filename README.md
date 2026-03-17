# OilRisk-Alert

基于多源数据与 Agent 的原油价格风险智能预警系统。

采用三专家集成模型（LSTM + XGBoost + Stacking）进行 5 个交易日 WTI 原油价格风险预测，配合实时因子采集管道与 LLM 风险解读，通过 Web 界面展示风险仪表盘、因子分析、预警记录和模型回测。

---

## 架构

```
Vue 3 前端 (5173)  ──/api 代理──▶  Spring Boot 后端 (8080)  ──HTTP──▶  FastAPI 推理引擎 (5000)
                                         │                                    │
                                    MySQL 8.0 (3306)                   ML 模型 + 实时因子采集
```

<<<<<<< HEAD
| 组件 | 技术栈 | 端口 |
|------|--------|------|
| 前端 | Vue 3 + Vite + TypeScript + ECharts + Pinia + vue-i18n | 5173 |
| 后端 | Spring Boot 4.0.3 + MyBatis + MySQL | 8080 |
| 推理引擎 | FastAPI + PyTorch + XGBoost + SHAP | 5000 |
| 数据库 | MySQL 8.0 | 3306 |
=======
| 组件     | 技术栈                                                 | 端口 |
| -------- | ------------------------------------------------------ | ---- |
| 前端     | Vue 3 + Vite + TypeScript + ECharts + Pinia + vue-i18n | 5173 |
| 后端     | Spring Boot 4.0.3 + MyBatis + MySQL                    | 8080 |
| 推理引擎 | FastAPI + PyTorch + XGBoost + SHAP                     | 5000 |
| 数据库   | MySQL 8.0                                              | 3306 |
>>>>>>> 46eb64143eea85191fd330496e46020a19ed1baa

---

## 功能

### 风险总览
<<<<<<< HEAD
仪表盘评分(0-100)、5类因子雷达图、油价+风险双轴时序图（含预警标记）、三模型信号面板、AI 风险摘要（SSE 流式输出）、数据新鲜度状态栏

### 因子分析
SHAP 因子贡献条形图、权重调节滑块实时重算、权重演变历史趋势图、模型来源标注

### 预警记录
分页/筛选/排序、触发规则详情展开、AI 报告流式生成（生成后缓存到数据库）

### 模型回测
日期范围选择、LSTM/XGBoost/Stacking 三模型切换、多模型叠加对比图、准确率指标

### 其他特性
=======

仪表盘评分(0-100)、5类因子雷达图、油价+风险双轴时序图（含预警标记）、三模型信号面板、AI 风险摘要（SSE 流式输出）、数据新鲜度状态栏

### 因子分析

SHAP 因子贡献条形图、权重调节滑块实时重算、权重演变历史趋势图、模型来源标注

### 预警记录

分页/筛选/排序、触发规则详情展开、AI 报告流式生成（生成后缓存到数据库）

### 模型回测

日期范围选择、LSTM/XGBoost/Stacking 三模型切换、多模型叠加对比图、准确率指标

### 其他特性

>>>>>>> 46eb64143eea85191fd330496e46020a19ed1baa
- 中英文国际化切换
- 暗色 / 亮色主题切换
- LTTB 时序降采样（>2000 点自动触发）
- LLM 配置前端可视化管理

---

## ML 模型体系

```
原始数据 (CSV 400+列)
    ├── LSTM 趋势专家      27特征 × 30日窗口 → 价格预测 + 方向概率
    ├── XGBoost 冲击专家    ~40-50风险特征 → 下行风险评分
    └── Stacking 元学习器   Ridge回归, 9维输入 → pred_return_pct
         → 风险评分公式: score = 100 / (1 + exp(pct × 0.085))
```

风险级别：Low [0, 40) / Medium [40, 70) / High [70, 100]

---

## 实时因子采集

Python 端内置 4 个采集器，覆盖 36 个因子：

<<<<<<< HEAD
| 采集器 | 数据源 | 因子数 | 说明 |
|--------|--------|--------|------|
| yfinance | Yahoo Finance | 20 | 批量下载 + 分批限流 |
| FRED | 美联储经济数据 | 7 | REST API 直接调用 |
| EIA | 美国能源署 | 5 | 库存/产量数据 |
| GDELT | GDELT Project | 6 | 地缘政治情绪 |
=======
| 采集器   | 数据源         | 因子数 | 说明                |
| -------- | -------------- | ------ | ------------------- |
| yfinance | Yahoo Finance  | 20     | 批量下载 + 分批限流 |
| FRED     | 美联储经济数据 | 7      | REST API 直接调用   |
| EIA      | 美国能源署     | 5      | 库存/产量数据       |
| GDELT    | GDELT Project  | 6      | 地缘政治情绪        |
>>>>>>> 46eb64143eea85191fd330496e46020a19ed1baa

- APScheduler 定时调度：每交易日 06:00 (Asia/Shanghai) 自动采集
- 启动时自动检测 90 天数据缺口并回填
- 采集 → 推理 → 写入 risk_index/risk_factor/alert 表，全链路自动化
- DB 连接失败时回退 CSV 模式

---

## 用户配置指南

### 1. 数据库

安装 MySQL 8.0，手动创建数据库：

```sql
CREATE DATABASE oilrisk CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

然后执行建表脚本（6 张表，`CREATE TABLE IF NOT EXISTS`，可重复执行）：

```bash
mysql -u root -p oilrisk < src/main/resources/schema.sql
```

### 2. 后端配置 — `src/main/resources/application.properties`

需修改以下配置项：

```properties
# ---- 数据库连接（必须）----
spring.datasource.url=jdbc:mysql://localhost:3306/oilrisk?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=UTF-8
spring.datasource.username=root          # 改为你的 MySQL 用户名
spring.datasource.password=123456        # 改为你的 MySQL 密码

# ---- LLM API（可选，不配置则回退 Mock 模板）----
llm.api.key=                             # 你的 LLM API Key
llm.api.url=https://apis.iflow.cn/v1/chat/completions   # LLM 接口地址
llm.api.model=qwen3-max                  # 模型名称
```

> LLM 配置也可在前端界面通过弹窗实时修改，无需重启。

### 3. Python 推理引擎配置 — `python_engine/.env`

复制示例并填写：

```env
# ---- 数据源 API Key（必须，否则对应采集器无法工作）----
FRED_API_KEY=你的FRED密钥              # 申请地址: https://fred.stlouisfed.org/docs/api/api_key.html
EIA_API_KEY=你的EIA密钥                # 申请地址: https://www.eia.gov/opendata/register.php

# ---- 网络代理（中国大陆环境必须）----
# 无代理时 FRED/EIA/GDELT 会因 GFW 干扰导致 SSL EOF
HTTPS_PROXY=http://127.0.0.1:7890      # 改为你的代理地址和端口
HTTP_PROXY=http://127.0.0.1:7890

# ---- yfinance 限流（可选，默认值通常足够）----
YF_BATCH_SIZE=5
YF_BATCH_DELAY=2.0
YF_SINGLE_DELAY=1.5

# ---- 启动行为（可选）----
BACKFILL_ON_STARTUP=true               # 启动时自动检测并回填数据缺口
COLLECT_ON_STARTUP=false               # 启动时是否立即触发一次采集

# ---- SSL 调试（可选）----
# SSL_VERIFY=false                     # 仅在调试 SSL 问题时启用
```

### 4. 配置项速查

<<<<<<< HEAD
| 配置项 | 位置 | 必须 | 说明 |
|--------|------|------|------|
| MySQL 用户名/密码 | `application.properties` | 是 | 数据库连接凭据 |
| 建库 + 建表 | MySQL 手动执行 | 是 | 建库 `oilrisk` + 执行 `schema.sql` |
| `FRED_API_KEY` | `python_engine/.env` | 是 | 美联储经济数据 API |
| `EIA_API_KEY` | `python_engine/.env` | 是 | 美国能源署 API |
| `HTTPS_PROXY` / `HTTP_PROXY` | `python_engine/.env` | 中国大陆必须 | 代理地址，解决 SSL 连接问题 |
| `llm.api.key` | `application.properties` | 否 | LLM API Key，不配置则使用 Mock 模板 |
| `llm.api.url` | `application.properties` | 否 | LLM 接口地址 |
| `llm.api.model` | `application.properties` | 否 | LLM 模型名称 |
=======
| 配置项                           | 位置                       | 必须         | 说明                                   |
| -------------------------------- | -------------------------- | ------------ | -------------------------------------- |
| MySQL 用户名/密码                | `application.properties` | 是           | 数据库连接凭据                         |
| 建库 + 建表                      | MySQL 手动执行             | 是           | 建库 `oilrisk` + 执行 `schema.sql` |
| `FRED_API_KEY`                 | `python_engine/.env`     | 是           | 美联储经济数据 API                     |
| `EIA_API_KEY`                  | `python_engine/.env`     | 是           | 美国能源署 API                         |
| `HTTPS_PROXY` / `HTTP_PROXY` | `python_engine/.env`     | 中国大陆必须 | 代理地址，解决 SSL 连接问题            |
| `llm.api.key`                  | `application.properties` | 否           | LLM API Key，不配置则使用 Mock 模板    |
| `llm.api.url`                  | `application.properties` | 否           | LLM 接口地址                           |
| `llm.api.model`                | `application.properties` | 否           | LLM 模型名称                           |
>>>>>>> 46eb64143eea85191fd330496e46020a19ed1baa

---

## 启动

**按以下顺序启动：**

```bash
# 1. 确保 MySQL 运行，且已完成建库建表

# 2. Python 推理引擎
cd python_engine
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000

# 3. Spring Boot 后端
./mvnw spring-boot:run
# 或 IDE 中直接运行 OilRiskAlertApplication.java

# 4. 前端
cd frontend
npm install
npm run dev
```

启动后访问 http://localhost:5173

---

## 目录结构

```
OilRisk_Alert/
├── src/main/java/.../oilrisk_alert/    # Java 后端
│   ├── controller/                      # REST 控制器（7 个）
│   ├── service/                         # 业务逻辑
│   ├── mapper/                          # MyBatis Mapper
│   ├── entity/ dto/ vo/                 # 数据模型
│   ├── config/                          # CORS、LLM、权重配置
│   └── common/                          # 异常处理、统一响应
├── src/main/resources/
│   ├── application.properties           # 后端配置 ← 需修改
│   ├── schema.sql                       # 建表脚本 ← 需执行
│   └── mapper/*.xml
├── frontend/                            # Vue 前端
│   └── src/
│       ├── views/                       # 4 个页面
│       ├── components/charts/           # ECharts 图表组件（5 个）
│       ├── composables/                 # 组合式函数
│       ├── stores/                      # Pinia 状态
│       ├── i18n/                        # 国际化
│       └── api/                         # Axios 请求层
├── python_engine/                       # FastAPI 推理引擎 + 因子采集
│   ├── app.py                           # FastAPI 入口
│   ├── engine.py                        # 三模型推理引擎
│   ├── db.py                            # SQLAlchemy 数据层
│   ├── collector/                       # 4 个数据采集器 + 调度器
│   ├── .env                             # 环境变量 ← 需修改
│   └── requirements.txt
├── OilRisk_System/                      # ML 模型文件 + 训练脚本
│   ├── best_lstm.pt                     # LSTM 权重
│   ├── xgb_wti_shock_model.pkl          # XGBoost 模型
│   ├── meta_ridge_model.pkl             # Stacking 元学习器
│   └── *.pkl                            # Scaler + 特征列名
├── data/                                # 数据集
└── doc/                                 # 需求文档、设计文档
```

---

## 数据库表

<<<<<<< HEAD
| 表名 | 说明 |
|------|------|
| `risk_index` | 每日风险评分（0-100）、级别、油价 |
| `risk_factor` | SHAP 因子贡献值（按日期 × 因子） |
| `alert` | 预警记录（级别、触发规则、AI 报告缓存） |
| `factor_realtime` | 实时采集的因子原始值 |
| `collection_log` | 采集日志（来源、成功/失败数、耗时） |
| `system_state` | 系统状态键值对（最后采集/推理时间等） |
=======
| 表名                | 说明                                    |
| ------------------- | --------------------------------------- |
| `risk_index`      | 每日风险评分（0-100）、级别、油价       |
| `risk_factor`     | SHAP 因子贡献值（按日期 × 因子）       |
| `alert`           | 预警记录（级别、触发规则、AI 报告缓存） |
| `factor_realtime` | 实时采集的因子原始值                    |
| `collection_log`  | 采集日志（来源、成功/失败数、耗时）     |
| `system_state`    | 系统状态键值对（最后采集/推理时间等）   |
>>>>>>> 46eb64143eea85191fd330496e46020a19ed1baa
