# 项目配置文档任务记录

时间：2026-03-29

本次任务：检索 `OilRisk_Alert` 项目，生成配置文档 Markdown。

## 已完成的关键操作

1. 检索仓库结构，确认项目由 `frontend`、`Spring Boot`、`python_engine`、`OilRisk_System` 四部分组成。
2. 读取并核对以下配置文件：
   - `src/main/resources/application.properties`
   - `src/test/resources/application.properties`
   - `src/main/resources/schema.sql`
   - `frontend/package.json`
   - `frontend/vite.config.ts`
   - `frontend/src/api/index.ts`
   - `python_engine/.env`
   - `python_engine/requirements.txt`
   - `python_engine/app.py`
   - `python_engine/db.py`
   - `python_engine/engine.py`
   - `python_engine/collector/scheduler.py`
   - `python_engine/collector/registry.py`
3. 核实前后端端口链路：
   - 前端 `5173`
   - 后端 `8080`
   - Python 引擎 `5000`
4. 核实数据库配置分散在两处：
   - Spring Boot 读 `application.properties`
   - Python 读环境变量
5. 统计因子注册表文本中的因子数量：
   - 总数 `38`
   - `yfinance=20`
   - `fred=7`
   - `eia=5`
   - `gdelt=6`
6. 创建正式文档：
   - `docs/项目配置文档.md`
7. 明确区分两种运行目标：
   - 最小可运行：只要求 MySQL + 本地模型/历史数据可用
   - 完整功能运行：额外要求 FRED / EIA / LLM API 与外网访问能力
8. 根据代码确认外部依赖性质：
   - LLM API 不是启动硬依赖，缺失时退回 Mock
   - FRED / EIA 是实时采集链路的强依赖
   - Yahoo Finance / GDELT 不需要用户提供 Key，但需要网络可访问

## 本次发现的关键问题

1. `README.md` 存在未解决的 Git 冲突标记，不能作为可靠说明文档。
2. `application.properties` 明文保存数据库密码和 LLM API Key，有泄露风险。
3. 本机默认 Python 为 `3.7.0`，无法兼容 `python_engine` 当前代码语法，实际需要 Python 3.10+。
4. 仓库缺少 `mvnw` / `mvnw.cmd`，README 中的 Maven Wrapper 启动方式当前不可直接执行。
5. Python 与 Spring Boot 数据库配置未统一，后续维护时容易漂移。

## 后续维护注意事项

1. 后续如果改端口，需要同时检查：
   - `frontend/vite.config.ts`
   - `src/main/resources/application.properties`
   - `src/main/java/.../CorsConfig.java`
2. 后续如果改数据库账号密码，需要同时检查：
   - Spring Boot 主配置
   - Python `.env` 或环境变量
3. 后续如果改模型目录或数据文件位置，需要同步检查：
   - `python_engine/engine.py`
   - `OilRisk_System/`
   - `data/Final_Oil_Dataset_Cleaned.csv`
4. 若要把 LLM 配置改成持久化，当前 `/api/config/llm` 只改内存，不会在重启后保留。
