# SmartTraffic 最终交付计划

本文档用于 Stage 9 最终交付前审计和文档收口，并记录后续 Full Stage DB 迁移边界。它只描述计划、边界和检查清单，不引入非当前阶段核心业务功能、权限系统、生产部署或新 tag。

## 1. 当前版本状态

当前已完成 Stage 9EF 最终验收准备。最新工程交付 commit 是 Stage 9CD 后的 `5538a3a`，当前建议 final engineering delivery tag 为 `v0.9.0-final-engineering-delivery`。该 tag 不是 `v1.0.0`，不代表 DB-backed final version、production deployment 或执法级系统。Full Stage 1AB 已在最终交付后补充 DB Foundation：SQLAlchemy Declarative Base、engine/session dependency、Alembic baseline 和 `SMARTTRAFFIC_DATABASE_URL` 已接入。Full Stage 1CD 已新增 core models、业务表 migration、repositories 和 CRUD tests。Full Stage 1EF 已新增 artifact compatibility / import / read-through helper 和 dry-run CLI。Full Stage 2AB 已完成 Video API、Processing Task 生命周期和 `traffic_analysis_runs` run index 的 DB-backed 迁移；Full Stage 2CD 已完成 detections、tracks、trajectory_points、flow_counts、zone_statistics 和 Traffic Analysis Center DB-first index；Full Stage 3AB 已完成 Zone / Event Rule DB CRUD、run-level config snapshot 和 top-level Event APIs；Full Stage 3CD 已完成 Event / EventEvidence / RuleExecution DB lifecycle、Alert Center DB 状态流转、Review DB workflow / `review_comments` audit trail，以及 rule rerun request 的 `processing_tasks.mode=rule_rerun` 记录；Full Stage 3EF 已完成 Bad Case DB workflow、Evaluation Dataset / Result DB workflow、failed cases DB persistence 方案和 failed-case -> Bad Case DB 转换；Full Stage 4AB 已完成 Trajectory final features 和六类 Event Rule final behavior；Full Stage 4CD 已完成 Detection / Tracking benchmark algorithm foundation；Full Stage 4E 已完成 Bad Case deterministic replay / rule replay regression evaluation；Full Stage 5AB 已完成 ZoneEditor UI + API integration；Full Stage 5CD 已完成 Video Overlay UI + EventTimeline；Full Stage 5E 已完成 Review UX + Evaluation UI；Full Stage 6AB 已完成 Report Center 页面、Report API、CSV export 和 JSON export；Full Stage 6CD 已完成 PDF export、report bundle metadata、keyframe summary 和 annotated video artifact reference；Full Stage 7AB 已完成 Cameras DB API、stream_url masking、realtime preview metadata、recent frame/event/alert cache、`processing_tasks.mode=realtime_process` 记录和 Camera Center 最小前端接入；Full Stage 7CD 已完成 minimal actor identity、permissive / strict permission guard、audit actor propagation、API error handling、request id logging、DB readiness check 和 security / ops docs。Stage 1-9 已完成 artifact-backed MVP 与最终工程交付准备主链路：

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
- Traffic Analysis Center artifact-compatible MVP，包括 manifest、artifact index、statistics、visual artifacts、Analysis Runs API 和前端最小视图；核心 result index / detections / tracks / trajectory_points / flow_counts / zone_statistics 已 DB-first。
- Review Center artifact-backed MVP，包括 review artifacts、Review API、React 页面和 Analysis / Alert 定位联动。
- Bad Case Center artifact-backed MVP，包括 `bad_cases.jsonl`、schema、service、API、React 页面、from-review 和 from-failed-case。
- Evaluation Center artifact-backed MVP，包括 dataset / run / result / failed-case artifacts、MVP metrics、API、CLI、React 页面和 Bad Case regression summary MVP。
- Docker Compose 本地开发骨架。
- Full Stage 1AB DB Foundation：SQLAlchemy / Alembic / Session / Config 基础接入，默认 SQLite 本地验证。
- Full Stage 1CD Core Models / Migrations / Repositories：核心业务表 schema、repository CRUD foundation 和测试已完成，但未接入业务 service。
- Full Stage 1EF Artifact Compatibility：旧 run artifacts discovery、结构化导入 DB、DB 优先 read-through fallback 和 CLI 已完成，但未改变现有 API 默认行为。
- Full Stage 2AB Video / Processing DB-backed foundation：Video upload/list/detail/status/frames、Processing Task 状态/进度/时间/错误信息、以及同一 video 多 run index 已接入 DB，同时保留本地 artifact 生成。
- Full Stage 2CD Result Persistence：detections、tracks、trajectory_points、flow_counts、zone_statistics 和 Traffic Analysis Center DB index 已接入 DB-first / artifact fallback，同时保留本地 artifact 生成。
- Full Stage 3AB Config / Event API DB flow：Zone / Event Rule CRUD、version 字段、run-level config snapshot、top-level Event APIs、Event status update 和 Event -> Bad Case 最小 DB linkage 已完成；前端 ZoneEditor 未在本阶段改造。
- Full Stage 3CD Event / Alert / Review DB lifecycle：EventEvidence、RuleExecution、Alert status transitions、Review action audit trail、false-negative DB records 和 rule rerun request task 已接入 DB-first / artifact fallback；未执行真实规则重跑。
- Full Stage 3EF Bad Case / Evaluation DB workflow：Bad Case list/detail/create/update/filter/summary、from-review、from-failed-case、Evaluation dataset/result、failed cases persistence 和 `run_evals.py --write-db` 已接入 DB-first / artifact fallback。
- Full Stage 4AB Trajectory / Event Rules：TrajectoryEngine 已输出 `zone_history`、`lane_relation`、`line_crossings`、dwell/speed/moving_angle/direction consistency 和 center / bottom-center 策略；wrong_way、illegal_parking、danger_zone、pedestrian_lane、congestion、flow_counting 六类规则已补齐 final behavior；速度仍是像素级估计。
- Full Stage 4CD Detection / Tracking benchmark：已实现 IoU、按 class matching、precision、recall、VOC-style single-IoU AP/mAP、per-class AP、frame-level tracking association、IDF1、MOTA、ID switch、track lost、insufficient-data handling，并可写入 DB-backed `evaluation_results`；该实现不是 COCO official mAP 或 TrackEval official implementation。
- Full Stage 4E Regression Evaluation：已实现 status-based deterministic replay、stored rule replay fixture、per-case regression result、failed regression cases、`regression_pass_rate`、fixed / reopened / failed counts、DB-backed evaluation result persistence 和 CLI/API config 透传；`apply_updates=false` 为默认策略，完整视频级 rerun 不在本阶段。
- Full Stage 5AB ZoneEditor UI：已将 ZoneEditor 从 placeholder 改为真实交互组件，支持 polygon、direction line、counting line 绘制，DB-backed zones / event_rules 保存、更新、删除、读取回显，enabled/version 展示，基础 loading/error/empty 状态和前端 utility tests。
- Full Stage 5CD Video Overlay / EventTimeline：DetectionOverlay、TrackOverlay 和 Zone overlay 已不再是 placeholder；AnalysisDetailPage 已接入 detections、tracks、trajectory_points、zones 和 events 数据叠加展示；EventTimeline 支持过滤、选中和点击事件跳转到对应 timestamp。
- Full Stage 5E Review UX + Evaluation UI：ReviewDrawer 支持 confirm / false_positive / false_negative / ignore / resolve、comments、Review -> Bad Case 和 rule rerun request；Evaluation Center 支持 dataset/run/type selector、result cards、detail JSON、failed cases table、failed-case -> Bad Case、regression summary 和边界标签。
- Full Stage 6AB Report Center：已新增 `/api/reports` run list / summary / JSON export / CSV export，支持 events、alerts、flow_counts、zone_statistics、bad_cases、evaluation_results 六类导出；前端新增 Report Center 页面、run selector、summary cards、CSV download、JSON preview/download、loading/error/empty 状态和非执法边界提示。
- Full Stage 6CD Report Export：已新增 `/api/reports/{run_id}/export.pdf`、`/api/reports/{run_id}/bundle`、keyframe summary、annotated video artifact reference、前端 PDF download 和 bundle / visual artifact summary panel；PDF 与 bundle 均不写入仓库，不复制大视频或图片。
- Full Stage 7AB Camera / Realtime Preview：已新增 DB-backed Cameras API、`upload` / `rtsp` / `file` / `mock` source_type、enable / disable、`stream_url` masking、mock stream preview、local file smoke-level preview、RTSP no-connect preview、recent frames / events / alerts bounded cache、`processing_tasks.mode=realtime_process` linkage、Camera Center 最小前端页面、后端与前端测试和文档。该阶段不是 production realtime monitoring。
- Full Stage 7CD Security / Audit / Ops：已新增 `X-SmartTraffic-Actor` / `X-SmartTraffic-Role` minimal identity、`SMARTTRAFFIC_AUTH_MODE=permissive|strict`、strict-mode preview permission guard、关键写操作 actor propagation、structured audit logging、标准错误响应、request id logging、`/health/ready` DB readiness、env/docs hardening 和测试。该阶段不是 production IAM。
- Stage 9AB final pre-delivery audit and documentation closeout。
- Stage 9CD 小型 demo/sample config、toy expected annotations、seed script、Makefile 和环境命令收口。
- Stage 9EF final acceptance and final tag preparation。
- pytest、frontend build、Node utility tests、danger check 和文档化自查命令。

## 3. 未完成边界

- DB-backed final version。
- DB-backed full business API/service migration 和生产级持久化查询层。
- COCO official mAP / public dataset benchmark。
- TrackEval official IDF1 / MOTA benchmark。
- Real dataset benchmark。
- Complete video-level Bad Case rerun pipeline；当前是 deterministic replay / rule replay。
- Production-grade evaluation platform。
- Production realtime streams、production IAM、central audit storage、Permissions / multi-user audit、Security hardening；留给 Full Stage 8。
- Full final release hardening、production deployment readiness、monitoring readiness 和 `v1.0.0`；留给 Full Stage 8。
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
- 不做不属于当前阶段的数据库 migration。
- 不做 production IAM；Full Stage 7CD 只提供 minimal local actor / permission preview。
- 不做 production realtime stream；Full Stage 7AB/7CD 只提供 realtime preview metadata 和安全预览。
- 不做生产部署。
- 不做模型训练。
- 不下载或提交大视频、数据集或模型权重。
- 不移动、删除或重建已有 tag。
- 不把 artifact-backed MVP 文档写成 DB-backed final version。
- 不把 VOC-style single-IoU mAP / lightweight IDF1 / MOTA 写成 COCO official 或 TrackEval official。
