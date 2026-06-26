# SmartTraffic 最终交付计划

本文档用于 Stage 9AB 最终交付前审计和文档收口。它只描述计划、边界和检查清单，不引入核心业务功能、数据库迁移、权限系统、生产部署或新 tag。

## 1. 当前版本状态

当前稳定节点是 `v0.8.0-bad-case-evaluation-mvp`，指向 Stage 8HI 后的 `d1f5bf7`。Stage 1-8 已完成 artifact-backed MVP 主链路：

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
- pytest、frontend build、Node utility tests、danger check 和文档化自查命令。

## 3. 未完成边界

- DB-backed final version。
- Database migrations、repositories 和生产级持久化查询层。
- Industrial-grade mAP / IDF1 / MOTA。
- Real dataset benchmark。
- Real rerun-based Bad Case regression pipeline。
- Production-grade evaluation platform。
- Permissions / multi-user audit。
- Realtime streams。
- Production deployment、monitoring 和 security hardening。
- Law-enforcement-grade violation judgement。

## 4. Stage 9CD 计划：Demo / Sample / Docker / 环境收口

Stage 9CD 建议只做交付可运行性收口：

- 准备小型 sample config，例如 zone / rule / evaluation dataset registry 示例。
- 为 demo seed 提供 toy metadata / config 生成能力，不生成或提交真实大视频、真实模型权重或大规模结果。
- 明确 Docker Compose 本地启动流程和常见环境变量。
- 补充 Node 版本要求，建议本地使用 Node 20+，Docker Compose frontend 已使用 `node:20-alpine`。
- 补充一条 dry-run demo 路径，确保无模型权重也可演示基础链路。
- 保持 `samples/videos/`、`local_videos/`、`local_models/` 和 `results/` 只提交 `.gitkeep` 或小型文本配置。

Stage 9CD 不应实现新业务中心、数据库迁移、真实数据下载器、模型训练或生产部署。

## 5. Stage 9EF 计划：最终验收 / Tag

Stage 9EF 建议在 Stage 9CD 完成后再执行：

- 运行后端全量测试、前端测试、前端 build、`docker compose config`、`git diff --check` 和 `scripts/danger_check.py`。
- 扫描 tracked forbidden files、敏感词、大文件、生成结果、视频、模型权重、cache、dist 和 node_modules。
- 确认 README、API reference、architecture、database schema、evaluation、demo plan 和 final delivery plan 一致。
- 确认旧 tag 未移动。
- 用户明确要求后，才创建最终交付 tag。

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
- `cd backend && python3 -m pytest tests` 通过。
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
