# Docker 化任务记录

时间：2026-03-29

本次任务：为 `OilRisk_Alert` 增加 Docker 部署配置，并提供一个交互式 Python 脚本，让用户按提示完成配置并可直接启动容器。

## 已完成的关键操作

1. 将后端配置改为环境变量优先：
   - `src/main/resources/application.properties`
   - 支持数据库、Python 引擎地址、LLM 配置、CORS 来源通过环境变量注入
2. 将 CORS 改为可配置：
   - `src/main/java/com/example/oilrisk_alert/config/CorsConfig.java`
   - 支持通过 `APP_CORS_ALLOWED_ORIGINS` 传入多个来源
3. 新增 Docker 编排文件：
   - `docker-compose.yml`
   - 包含 `mysql`、`python-engine`、`backend`、`frontend` 四个服务
4. 新增三个镜像构建文件：
   - `docker/backend.Dockerfile`
   - `docker/python-engine.Dockerfile`
   - `docker/frontend.Dockerfile`
5. 新增 Nginx 前端代理配置：
   - `docker/nginx.conf`
   - 负责静态资源服务和 `/api` 反向代理
6. 新增示例环境变量模板：
   - `.env.example`
7. 新增交互式配置脚本：
   - `scripts/setup_docker.py`
   - 功能：
     - 提示输入数据库、端口、数据源、LLM 配置
     - 自动生成根目录 `.env`
     - 若已有 `.env`，自动备份为 `.env.backup.<timestamp>`
     - 可选直接执行 `docker compose up --build -d`
8. 新增 `.dockerignore` 以减少 Docker 构建上下文体积。
9. 更新 `.gitignore`：
   - 忽略 `.env.backup.*`

## 已完成的验证

1. `python -m py_compile scripts/setup_docker.py` 通过。
2. `docker compose --env-file .env.example config` 通过。
3. 已删除验证过程中生成的 `scripts/__pycache__`，未遗留临时文件。
4. `docker compose --env-file .env.example build` 已通过。
5. `docker compose --env-file .env.example up -d` 已成功启动四个服务。
6. 已验证以下接口可正常响应：
   - `GET http://localhost:5000/health`
   - `GET http://localhost:8080/api/system/status`
   - `GET http://localhost:5173/api/system/status`
7. 已手动调用 `POST http://localhost:5000/predict/daily`，确认 Python 推理结果可以写入 MySQL，随后：
   - `GET http://localhost:8080/api/risk/current` 返回正常数据
   - `GET http://localhost:5173/api/risk/current` 通过前端代理返回正常数据
8. 验证完成后已执行 `docker compose --env-file .env.example down`，未持续占用端口。

## 关键设计决策

1. 不再依赖仓库内硬编码密钥运行 Docker。
   - 后端改为从环境变量读取敏感配置。
2. 前端采用 Nginx 统一对外暴露。
   - 避免浏览器跨域问题。
   - `/api` 走同域代理，SSE 也能正常转发。
3. Python 引擎继续使用环境变量，而不是强依赖 `python_engine/.env`。
   - Docker 场景下由 Compose 直接注入。
4. 用户配置入口统一为根目录 `.env`。
   - 降低理解成本。
   - 便于 `docker compose` 默认读取。

## 当前已知注意事项

1. 已完成完整 `docker compose` 实机启动验证。
   - 本次已完成 build / up / 接口验证 / down。
2. Python 推理镜像包含 `torch`、`xgboost`、`shap`，首次构建时间很长，且镜像体积较大。
3. 宿主机 Docker 默认镜像拉取链路曾指向 `docker.mirrors.ustc.edu.cn` 并返回 EOF。
   - 处理方式：Dockerfile 基础镜像已切换到 `docker.m.daocloud.io/library/...`
4. 前端曾存在一个会阻断容器构建的 TypeScript 错误：
   - 文件：`frontend/src/components/charts/PriceRiskAlertChart.vue`
   - 问题：未使用变量 `visibleCount`
   - 处理：已删除该变量
5. 如果用户在中国大陆网络环境下运行且需要实时采集，通常仍需要代理。
6. 交互脚本本身已兼容本机 Python 3.7，但项目的 Python 推理服务代码本身仍建议运行在 Python 3.10+ 环境中；Docker 镜像已固定为 `python:3.11-slim`。
