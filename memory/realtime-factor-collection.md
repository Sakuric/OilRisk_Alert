# 实时因子获取需求 — 开发记录

> 完成日期：2026-03-10
> 最后更新：2026-03-14（第四轮修复 — 风险公式校准+UI优化+模型标注）

---

## 一、交付物清单

### Python 端（12 个文件）

| 文件 | 类型 | 说明 |
|------|------|------|
| `python_engine/db.py` | 新增 | SQLAlchemy + PyMySQL 连接池、ORM模型、CRUD |
| `python_engine/collector/__init__.py` | 新增 | 包初始化 |
| `python_engine/collector/base.py` | 新增 | FactorCollector ABC 基类（3次重试、指数退避） |
| `python_engine/collector/registry.py` | 新增 | FACTOR_REGISTRY 36个因子 + VALIDATION_RANGES |
| `python_engine/collector/http_utils.py` | **新增(3/13)** | 共享HTTP session工厂（代理+SSL重试+UA伪装） |
| `python_engine/collector/yfinance_collector.py` | **重写(3/13)** | 批量下载+分批限流+失败逐个重试 |
| `python_engine/collector/fred_collector.py` | **重写(3/13)** | 弃用fredapi，直接requests+共享session |
| `python_engine/collector/eia_collector.py` | **改造(3/13)** | 使用共享HTTP session |
| `python_engine/collector/gdelt_collector.py` | **改造(3/13)** | 使用共享HTTP session |
| `python_engine/collector/scheduler.py` | **改造(3/13)** | +缺口检测+回填+交易日范围 |
| `python_engine/engine.py` | 改造 | 新增 reload_from_db() 方法 |
| `python_engine/app.py` | **改造(3/13)** | +启动时自动回填+3个新API |

### Java 端（7 个文件）

| 文件 | 类型 | 说明 |
|------|------|------|
| `SystemStatusController.java` | 新增 | GET /api/system/status, POST /api/collect/trigger, GET /api/collect/log |
| `SystemStatusService.java` | 新增 | 服务接口 |
| `SystemStatusServiceImpl.java` | 新增 | 服务实现（RestTemplate 调用 Python 端） |
| `SystemStatusVO.java` | 新增 | 系统状态VO + FactorCoverageVO |
| `CollectResultVO.java` | 新增 | 采集结果VO + CollectionDetail + PredictionSummary |
| `RiskCurrentVO.java` | 改造 | +dataDate, updatedAt, dataSource |
| `RiskServiceImpl.java` | 改造 | getCurrentRisk() 填充新字段 |

### 前端（6 个文件）

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/types/system.ts` | 新增 | SystemStatusVO, CollectResultVO 类型 |
| `frontend/src/api/system.ts` | 新增 | getSystemStatus(), triggerCollect() |
| `frontend/src/composables/useDataFreshness.ts` | 新增 | 60s轮询、新鲜度计算、自动刷新 |
| `frontend/src/views/RiskOverview.vue` | 改造 | 顶部数据状态栏 |
| `frontend/src/i18n/zh-CN.ts` | 改造 | dataStatus 中文翻译 |
| `frontend/src/i18n/en-US.ts` | 改造 | dataStatus 英文翻译 |

### 数据库

- `schema.sql` 追加 3 张表：`factor_realtime`, `collection_log`, `system_state`

---

## 二、2026-03-13 修复记录（SSL/Rate Limit + 回填机制）

### 问题根因

| 问题 | 根因 | 影响 |
|------|------|------|
| yfinance 0/20 全失败 | 逐ticker调用触发Yahoo Rate Limit | 所有P0/P1日频因子无数据 |
| FRED/EIA/GDELT SSL EOF | 中国网络GFW干扰HTTPS到美国政府API | 所有FRED/EIA/GDELT因子无数据 |
| 前端显示老数据 | 25年12月后采集全部失败+无回填机制 | 风险概览/因子分析/预警记录全部过期 |

### 修复措施

#### 1. 新增 `collector/http_utils.py` — 共享HTTP会话工厂
- 代理支持：读取 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量
- SSL重试：urllib3 Retry策略（3次+指数退避+状态码429/5xx）
- SSL验证可关闭：`SSL_VERIFY=false`（调试用）
- UA伪装：Chrome UA避免反爬

#### 2. 重写 `yfinance_collector.py` — 批量下载+限流
- `yf.download(tickers=[...])` 批量下载替代逐个 `yf.Ticker().history()`
- 分批策略：每批5个ticker，批间延时2s（可配置）
- 失败回退：批量失败的ticker逐个重试，每个间隔1.5s
- 环境变量：`YF_BATCH_SIZE`, `YF_BATCH_DELAY`, `YF_SINGLE_DELAY`

#### 3. 重写 `fred_collector.py` — 弃用fredapi
- 直接调用 FRED REST API（`api.stlouisfed.org/fred/series/observations`）
- 使用共享session → 自动获得代理+SSL重试能力
- 不再依赖fredapi库的内部HTTP实现

#### 4. 改造 EIA/GDELT — 使用共享session
- 替换原生 `requests.get()` 为 `get_shared_session().get()`

#### 5. 新增数据缺口检测与回填
- `detect_data_gaps(lookback_days)`: 检测最近N天交易日中缺失数据的日期
- `backfill_range(start, end)`: 逐日回填指定范围（带3s间隔）
- `detect_and_backfill()`: 自动检测+回填
- `db.get_factor_dates(start, end)`: 查询已有数据的日期集合

#### 6. 新增 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/collect/gaps` | GET | 检测数据缺口，`?lookback_days=90` |
| `/collect/backfill` | POST | 手动回填，body: `{startDate, endDate}` |
| `/collect/auto-backfill` | POST | 自动检测+回填，`?lookback_days=90` |

#### 7. 启动行为变更
- `BACKFILL_ON_STARTUP=true`（默认）：启动时自动检测90天内缺口并回填
- 原有 `COLLECT_ON_STARTUP` 保持不变

#### 8. 修复数据链路断点（推理结果→前端展示）
- **根因**：Python推理结果从未写入`risk_index`/`risk_factor`表，前端查的是空/旧表
- `db.persist_prediction(result)`: 将推理结果写入 risk_index + risk_factor
- `scheduler._run_collection()`: 推理后自动调用 `persist_prediction()`
- `app.py /predict/daily`: 改为先 `reload_from_db()` 再推理+持久化
- 回填时 `trigger_inference=True`：每天都执行推理+写表，确保历史数据完整

### 关键配置（.env）

```env
FRED_API_KEY=...
EIA_API_KEY=...

# 代理（解决SSL问题的首选方案）
HTTPS_PROXY=http://127.0.0.1:7890

# yfinance限流
YF_BATCH_SIZE=5
YF_BATCH_DELAY=2.0
YF_SINGLE_DELAY=1.5

# 启动行为
BACKFILL_ON_STARTUP=true
```

---

## 三、Bug 修复记录

| Bug | 严重性 | 归属 | 修复内容 |
|-----|--------|------|---------|
| registry 4个P2 column_name不匹配CSV | Critical | backend | 对照CSV实际列名修正（含括号后缀） |
| useDataFreshness watch不触发数据刷新 | Major | frontend | risk store 新增 fetchCurrentRisk/fetchTimeseries 方法 |
| triggerCollect API 超时10s不够 | Major | frontend | 超时改为 120s |
| API响应status大小写不一致 | Major | backend | Python返回值转小写 |
| API响应snake_case未转camelCase | Major | backend | getCollectionLogs 逐字段映射 |

## 四、残留 Minor 问题

1. `CollectResultVO.status` — Python端和TS类型大小写定义不一致（无运行时影响）
2. `SystemStatusVO.lastCollectionStatus = "UNAVAILABLE"` — 不在TS类型union中（行为正确）
3. `dataSource` 采集失败时仍返回 "realtime"（应仅SUCCESS/PARTIAL时返回）

## 五、验证结果（2026-03-13）

| 采集器 | 修复前 | 修复后 | 说明 |
|--------|--------|--------|------|
| yfinance | 0/20 (Rate Limited) | **20/20** | ^CRB退市→替换DBC |
| FRED | 0/7 (SSL EOF) | **6/7** | UMCSENT月频正常缺失 |
| EIA | 0/5 (SSL EOF) | **5/5** | 全部成功 |
| GDELT | 6/6(默认值) | **6/6** | 部分限流返回中性值 |

### 关键修复：CRB 指数
- `^CRB` 已退市 → 替换为 `DBC`（Invesco DB Commodity Tracking ETF）
- GOLD_VALUE 校验范围上调到 8000（金价已破5000）

### 代理配置
- 检测到 Clash Verge 代理运行在 `127.0.0.1:7897`
- 已写入 `.env`: `HTTPS_PROXY=http://127.0.0.1:7897`
- **代理是必须的**：无代理时 FRED/EIA/GDELT 全部 SSL EOF

## 六、关键注意事项

1. **环境变量**：Python端需配置 `FRED_API_KEY` 和 `EIA_API_KEY`，否则对应采集器无法工作
2. **代理是解决SSL问题的首选方案**：在中国网络环境下，FRED/EIA/GDELT的HTTPS连接会被GFW干扰，必须配置代理才能稳定采集
3. **当前代理端口 7897**（Clash Verge），如换代理软件需同步修改 .env
4. **MySQL**：需执行 schema.sql 中新增的建表语句创建 3 张新表
5. **依赖安装**：`python_engine/requirements.txt` 新增了 yfinance, fredapi, apscheduler, pymysql, sqlalchemy, pandas-market-calendars
6. **调度时区**：APScheduler 使用 Asia/Shanghai 时区，日频采集在每交易日 06:00
7. **容错机制**：DB连接失败时引擎回退到CSV模式，部分因子缺失时ffill填充
8. **registry.py 是数据管道核心**：column_name 必须与 CSV 列名完全一致，任何变更需同步验证
9. **回填注意**：大范围回填（如90天）耗时较长（每天约10-20s），yfinance对历史数据限流较宽松

## 七、2026-03-13 第二轮修复（异步采集+预警+权重+图表）

### 问题来源

| 问题 | 根因 | 修复 |
|------|------|------|
| 后端触发采集超时 Read timed out | `/collect/trigger` 同步执行耗时>120s | Python端改为后台线程异步执行 |
| 风险概览仪表盘显示0 | risk_index表无新数据(采集失败→无推理→无persist) | 数据管道修通后自然解决 |
| 走势图月份无分隔 | PriceRiskAlertChart xAxis无formatter | 添加月份格式化+interval按月显示 |
| 因子分析权重演变假数据 | FactorAnalysis.vue使用generateMockWeightData() | 全栈新建API，从risk_factor表真实查询 |
| 预警记录未更新 | persist_prediction不写alert表 | 新增_auto_generate_alert()自动生成预警 |
| dataSource采集失败仍返回realtime | 判断逻辑只排除INIT/空 | 改为仅SUCCESS/PARTIAL返回realtime |

### 修复文件清单

| 文件 | 修改类型 | 内容 |
|------|----------|------|
| `python_engine/app.py` | 改造 | `/collect/trigger`异步化(threading)+RUNNING状态+防并发锁 |
| `python_engine/db.py` | 改造 | `persist_prediction()`后自动调用`_auto_generate_alert()` |
| `SystemStatusServiceImpl.java` | 改造 | 处理异步trigger响应(status=started) |
| `CollectResultVO.java` | 改造 | +message字段 |
| `RiskServiceImpl.java` | 改造 | dataSource仅SUCCESS/PARTIAL时返回realtime |
| `FactorMapper.java` | 改造 | +findWeightHistory()方法 |
| `FactorMapper.xml` | 改造 | +findWeightHistory SQL(按date+category聚合ABS SHAP) |
| `FactorService.java` | 改造 | +getWeightHistory()接口 |
| `FactorServiceImpl.java` | 改造 | +getWeightHistory()实现(归一化为百分比) |
| `FactorController.java` | 改造 | +GET /api/factor/weight-history端点 |
| `frontend/src/types/system.ts` | 改造 | +RUNNING/UNAVAILABLE/started/already_running类型 |
| `frontend/src/composables/useDataFreshness.ts` | 改造 | 异步触发后5s轮询直到完成 |
| `frontend/src/views/RiskOverview.vue` | 改造 | collectResult显示兼容无collection字段 |
| `frontend/src/api/factor.ts` | 改造 | +getWeightHistory() API |
| `frontend/src/views/FactorAnalysis.vue` | 改造 | mock数据替换为真实API调用 |
| `frontend/src/components/charts/PriceRiskAlertChart.vue` | 改造 | xAxis月份格式化+按月间隔显示 |

### 预警自动生成逻辑

- 阈值: score>=65→High, >=45→Medium, >=30→Low
- 同日同级别不重复生成
- trigger_factor取top SHAP因子
- 自动生成中英文summary

## 八、2026-03-13 第三轮修复（推理引擎数据链路根因修复）

### 根因分析

| 根因 | 影响 | 严重性 |
|------|------|--------|
| schema.sql每次启动DROP TABLE+data.sql重新seed | 每次Java重启丢失所有采集/推理数据，回到seed状态 | Critical |
| `_build_lstm_features()`的dropna删除最新5行 | 推理永远基于5天前的数据，最新数据无法参与推理 | Critical |
| `reload_from_db()`只加载最新1天因子 | CSV(~Feb 2)到当前(Mar 12)有6周数据缺口未填充 | Critical |
| risk_factor.value DECIMAL(10,4)溢出 | volume类因子值>999999无法写入 | Major |

### 修复

| 文件 | 修改 |
|------|------|
| `schema.sql` | DROP TABLE → CREATE TABLE IF NOT EXISTS |
| `application.properties` | spring.sql.init.mode=always → never |
| `engine.py _build_lstm_features` | dropna()只基于feature列，不含y_price/y_label |
| `engine.py reload_from_db` | 改用get_all_factors_since，加载CSV结束后全部因子 |
| `db.py` | 新增get_all_factors_since(start_date)查询函数 |
| schema.sql risk_factor.value | DECIMAL(10,4) → DECIMAL(16,4) |

### 数据回填结果

- factor_realtime: 2025-12-15 ~ 2026-03-12（60个交易日）
- risk_index: 回填58个日期的推理结果
- risk_factor: 59个日期，300条SHAP记录
- alert: 自动生成56条预警记录

### 关键教训

1. **spring.sql.init.mode=always + DROP TABLE = 数据丢失定时炸弹**
2. **LSTM训练用的y列(shift(-HORIZON))不能参与推理时的dropna**
3. **reload_from_db必须填充CSV到当前的完整缺口，单天数据不足以构建可靠时序特征**

## 九、2026-03-14 第四轮修复（风险公式校准+UI优化+模型标注）

### 问题与修复

| 问题 | 根因 | 修复 |
|------|------|------|
| X轴标签过密（2015~2026全按月显示） | interval函数按月切换 | 2026前按年、2026后按月；默认显示最近20% |
| 风险分数全为100，无区分度 | 线性公式`50 - pct*10`对极端值无区分 | 改用sigmoid: `100/(1+exp(pct*0.085))`，k=0.085基于历史分布校准 |
| 风险概览页左栏底部空白 | flex布局未填充剩余空间 | `overview__col-left > :last-child { flex: 1 }` |
| 因子分析页无模型标注 | UI未显示模型来源 | 添加模型badge、SHAP/权重配置说明文字 |

### 风险公式校准细节

- Stacking 模型 pred_return_pct 实际分布：-24 ~ +9，均值 -10，标准差 8.15
- k=0.085 使 -10% → 70分（High阈值边界），保证Low/Medium/High三区间均有数据
- 回填后分布：Low=3, Medium=27, High=31，分数范围 31.9~88.3

### 关键教训

4. **风险公式必须基于模型输出的实际分布校准，不能拍脑袋设定线性系数**

## 十、2026-03-15 第五轮修复（4个遗留UI/模型问题）

### 修复清单

| 问题 | 根因 | 修复文件 | 修复方案 |
|------|------|----------|----------|
| 时间轴仍过密 | 标签粒度不随缩放自适应 | PriceRiskAlertChart.vue | 监听datazoom事件，按可见天数自动切换年/月/日粒度 |
| 风险分数全为100 | sigmoid k=0.085 对极端预测值饱和 | engine.py `_calc_risk_score` | 改用分段线性映射 `50 - pct*4`，截断[-30,30]，软夹[3,97] |
| 风险概览页空白 | grid/flex间距过大、左列350px过宽 | RiskOverview.vue CSS | 左列320px，gap 16px，图表容器自适应高度 |
| 因子分析页无模型公式 | 无公式展示组件 | FactorAnalysis.vue + i18n | 新增公式卡片：三步展示(R_base → ratio → R_final)，权重变动实时高亮 |

### 风险公式变更

**旧公式（sigmoid）**：`R = 100 / (1 + exp(pct × 0.085))`
- 问题：pct < -25 时 R > 89，极端值（如-50~-100）全部聚集在 95-100

**新公式（分段线性）**：`R = clamp(50 - pct × 4, 3, 97)`
- 映射关系: +10%→10, +5%→30, 0%→50, -5%→70, -10%→90
- 优势：全范围线性区分度，不存在饱和区，高风险区域差异清晰

### 时间轴粒度规则

| 可见天数 | 标签粒度 | 间隔 |
|----------|----------|------|
| > 365天 | 年 (2019, 2020...) | 年份变化时显示 |
| 90~365天 | 月 (2025-03, 2025-04...) | 月份变化时显示 |
| < 90天 | 日 (03-01, 03-02...) | 约每7天显示 |

### 注意事项

- 风险公式变更后，**历史 risk_index 表数据需重新计算**才能体现新的区分度
- 可通过触发回填（POST /collect/auto-backfill）重算历史推理结果
