# SmartTraffic 最终交付计划

本文档用于 Stage 9 最终交付前审计和文档收口。它只描述计划、边界和检查清单，不引入核心业务功能、数据库迁移、权限系统、生产部署或新 tag。

## 1. 当前版本状态

当前已完成 Stage 9EF 最终验收准备。最新工程交付 commit 是 Stage 9CD 后的 `5538a3a`，当前建议 final engineering delivery tag 为 `v0.9.0-final-engineering-delivery`。该 tag 不是 `v1.0.0`，不代表 DB-backed final version、production deployment 或执法级系统。Full Stage 1AB 已在最终交付后补充 DB Foundation：SQLAlchemy Declarative Base、engine/session dependency、Alembic baseline 和 `SMARTTRAFFIC_DATABASE_URL` 已接入。Full Stage 1CD 已新增 core models、业务表 migration、repositories 和 CRUD tests。业务 API、artifact import/read-through 和 service 层 DB-backed 迁移仍未完成；Full Stage 1EF 将处理 artifact compatibility / import / read-through，Full Stage 2 才开始 Video / Processing / Result Persistence 业务迁移。Stage 1-9 已完成 artifact-backed MVP 与最终工程交付准备主链路：

```text
video upload
-> metadata extraction
-> YOLOv8 detection
-> DeepSORT / mock tracking
-> Trajectory Engine
-> Event Engine
-> alert artifacts
-> traffic analysis artifacts
-> Review Center
-> Bad Case Center
-> Evaluation Center MVP
```

当前项目仍是本地开发和验证口径，不是数据库最终版、生产部署版或交通执法系统。

## 2. 已完成能力

- YOLOv8 / dry-run detection pipeline。
- DeepSORT adapter / deterministic mock tracking。
- Trajectory Engine 与轨迹 artifacts。
- Event Engine、六类规则回调、event evidence 和 rule execution artifacts。
- Alert Center artifact-backed MVP 和基础状态流转。
- Traffic Analysis Center artifact-backed MVP，包括 manifest、artifact index、statistics、visual artifacts、Analysis Runs API 和前端最小视图。
- Review Center artifact-backed MVP，包括 review artifacts、Review API、React 页面和 Analysis / Alert 定位联动。
- Bad Case Center artifact-backed MVP，包括 `bad_cases.jsonl`、schema、service、API、React 页面、from-review 和 from-failed-case。
- Evaluation Center artifact-backed MVP，包括 dataset / run / result / failed-case artifacts、MVP metrics、API、CLI、React 页面和 Bad Case regression summary MVP。
- Docker Compose 本地开发骨架。
- Full Stage 1AB DB Foundation：SQLAlchemy / Alembic / Session / Config 基础接入，默认 SQLite 本地验证。
- Full Stage 1CD Core Models / Migrations / Repositories：核心业务表 schema、repository CRUD foundation 和测试已完成，但未接入业务 service。
- Stage 9AB final pre-delivery audit and documentation closeout。
- Stage 9CD 小型 demo/sample config、toy expected annotations、seed script、Makefile 和环境命令收口。
- Stage 9EF final acceptance and final tag preparation。
- pytest、frontend build、Node utility tests、danger check 和文档化自查命令。

## 3. 未完成边界

- DB-backed final version。
- DB-backed business API/service migration、artifact compatibility / import / read-through 和生产级持久化查询层。
- Industrial-grade mAP / IDF1 / MOTA。
- Real dataset benchmark。
- Real rerun-based Bad Case regression pipeline。
- Production-grade evaluation platform。
- Permissions / multi-user audit。
- Realtime streams。
- Production deployment、monitoring 和 security hardening。
- Law-enforcement-grade violation judgement。

## 4. Stage 9CD 计划：Demo / Sample / Docker / 环境收口

Stage 9CD 已完成交付可运行性收口：

- 已准备小型 sample config：zone / rule / processing request。
- 已准备 toy expected events / counts，作为 Evaluation MVP smoke input。
- `scripts/seed_demo_data.py` 已提供 dry-run、force 和 output-root。
- Makefile 已补充 `docker-config`、`seed-demo` 和 venv 优先的 `backend-test`。
- Docker Compose 本地配置仍通过 `docker compose config`。
- README 和 demo plan 已说明 dry-run demo 路径、安全边界和 Makefile 命令。
- `samples/videos/`、`local_videos/`、`local_models/`、`results/` 和 `evals/results/` 仍不提交真实内容。

Stage 9CD 不应实现新业务中心、数据库迁移、真实数据下载器、模型训练或生产部署。

## 5. Stage 9EF：最终验收 / Tag 准备

Stage 9EF 用于最终验收和 final tag 准备：

- 运行后端全量测试、前端测试、前端 build、`docker compose config`、`git diff --check` 和 `scripts/danger_check.py`。
- 扫描 tracked forbidden files、敏感词、大文件、生成结果、视频、模型权重、cache、dist 和 node_modules。
- 确认 README、API reference、architecture、database schema、evaluation、demo plan 和 final delivery plan 一致。
- 确认旧 tag 未移动。
- 所有检查通过且用户明确要求后，才创建 `v0.9.0-final-engineering-delivery`。

`v0.9.0-final-engineering-delivery` 是最终工程交付里程碑，不是 production `v1.0.0`。

## 6. 数据与安全要求

- 不提交 `.env`、API key、token、password 或 secret。
- 不提交模型权重：`*.pt`、`*.pth`、`*.onnx`、`*.engine`。
- 不提交真实视频：`*.mp4`、`*.avi`、`*.mov`、`*.mkv`、`*.webm`。
- 不提交真实 `results/`、`evals/results/`、`local_models/`、`local_videos/` 内容。
- 不提交 `frontend/dist`、`node_modules`、venv、pytest / mypy / ruff cache。
- 允许保留必要 `.gitkeep` 和小型文档 / sample config。
- 项目输出不得作为正式交通执法依据。

## 7. 最终交付检查清单

- `git status -sb` clean。
- `git log --oneline` 顶部 commit 与预期一致。
- `git tag --points-at HEAD` 与当前阶段预期一致。
- `git ls-remote origin main` 与本地 main 同步。
- `git ls-remote --tags origin` 显示旧 tag 未移动。
- `git diff --check` 通过。
- `python3 -m compileall backend/app` 通过。
- `cd backend && ./.venv/bin/python -m pytest tests` 通过。
- `cd frontend && npm run build` 通过。
- `docker compose config` 通过。
- `python3 scripts/danger_check.py` 通过。
- 大文件、敏感词、tracked forbidden files 扫描无异常。

## 8. 不做事项

- 不新增核心业务功能。
- 不做数据库 migration。
- 不做权限系统。
- 不做实时流。
- 不做生产部署。
- 不做模型训练。
- 不下载或提交大视频、数据集或模型权重。
- 不移动、删除或重建已有 tag。
- 不把 artifact-backed MVP 文档写成 DB-backed final version。
- 不把 MVP metrics 写成 industrial-grade mAP / IDF1 / MOTA。
