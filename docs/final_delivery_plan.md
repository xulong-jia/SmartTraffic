# SmartTraffic 最终交付计划

本文档最初用于 Stage 9 最终交付前审计和文档收口；当前用于记录 final
local delivery baseline 与后续 spec completion patch 的边界。它只描述计划、
边界和检查清单，不引入生产部署或不属于当前本地验证范围的能力。

## 1. 当前版本状态

当前 `main` 已完成 SmartTraffic final local delivery baseline，并已在
`v1.0.0-smarttraffic-final-local-delivery` 上冻结本地交付基线。本轮
spec completion patch 继续只修复执行手册逐项审计发现的对齐缺口，不重打、
不移动已有 tag，也不改变 local validation prototype 的项目边界。Full Stage
1AB 已补充 DB Foundation：SQLAlchemy Declarative Base、engine/session
dependency、Alembic baseline 和 `SMARTTRAFFIC_DATABASE_URL` 已接入。Full
Stage 1CD 已新增 core models、业务表 migration、repositories 和 CRUD tests。
Full Stage 1EF 已新增 artifact compatibility / import / read-through helper
和 dry-run CLI。Full Stage 2AB 已完成 Video API、Processing Task 生命周期和
`traffic_analysis_runs` run index 的 DB-backed 迁移；Full Stage 2CD 已完成
detections、tracks、trajectory_points、flow_counts、zone_statistics 和 Traffic
Analysis Center DB-first index；Full Stage 3AB 已完成 Zone / Event Rule DB
CRUD、run-level config snapshot 和 top-level Event APIs；Full Stage 3CD 已
完成 Event / EventEvidence / RuleExecution DB lifecycle、Alert Center DB
状态流转、Review DB workflow / `review_comments` audit trail，以及
event-rules-only rule rerun 的 `processing_tasks.mode=rule_rerun` 记录和
结果落库；Full Stage 3EF 已完成 Bad Case DB workflow、Evaluation Dataset /
Result DB workflow、failed cases DB persistence 方案和 failed-case -> Bad
Case DB 转换；Full Stage 4AB 已完成 Trajectory final features 和六类 Event
Rule final behavior；Full Stage 4CD 已完成 Detection / Tracking benchmark
algorithm foundation 和 tracking failed-case 输出；Full Stage 4E 已完成 Bad
Case deterministic replay / rule replay regression evaluation；Full Stage 5AB
已完成 ZoneEditor UI + API integration；Full Stage 5CD 已完成 Video Overlay UI
+ EventTimeline；Full Stage 5E 已完成 Review UX + Evaluation UI；Full Stage
6AB 已完成 Report Center 页面、Report API、CSV export 和 JSON export；Full
Stage 6CD 已完成 PDF export、report bundle metadata、keyframe summary 和
annotated video artifact reference；Full Stage 7AB 已完成 Cameras DB API、
stream_url masking、realtime preview metadata、recent frame/event/alert
cache、`processing_tasks.mode=realtime_process` 记录和 Camera Center 最小前端
接入；Full Stage 7CD 已完成 minimal actor identity、permissive / strict
permission guard、audit actor propagation、API error handling、request id
logging、DB readiness check 和 security / ops docs。Stage 1-9 已完成
artifact-backed MVP 与最终工程交付准备主链路：

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

Final audit / docs consistency 已补充 `docs/final_acceptance_checklist.md`。
当前 final local delivery tag 是 `v1.0.0-smarttraffic-final-local-delivery`。

`v1.0.1-audit-polish` 是 v1.0.0 冻结后的 scoped audit polish：只修复
后审计发现的缺口，不移动、不重打 `v1.0.0-full-final-version`，也不新增
production IAM、production realtime、COCO official mAP、TrackEval official
metrics 或完整视频级 rerun claim。该小修使 `AlertPanel` / `EventTable`
不再是 contract-only 组件，使 `/api/processing/tasks` 读取 DB
`processing_tasks`，使 DB-backed processing 写入 detector/tracker
`model_runs`，并将 Stage 6 historical design note 标为 archived /
historical。

`v1.0.2-spec-alignment` 是 v1.0.1 后的 scoped spec-alignment 小修：只修复
逐句级执行手册审计发现的两个对齐问题，不移动、不重打
`v1.0.1-audit-polish` 或 `v1.0.0-full-final-version`。该小修使
`GET /api/analysis-runs/{run_id}/alerts` 按 run_id 优先读取 DB `alerts`
并保留 artifact fallback，同时将 ZoneEditor / event rule payload 的
severity 收敛为 EventEngine 支持的 `low` / `medium` / `high`。Alert
Center `level` 仍是独立概念，可继续使用 `info` / `warning` / `critical`。

`v1.0.3-final-hardening` 是 v1.0.2 后的 scoped final hardening 小修：只补齐
逐句级最终 hardening 发现的校验和文档边界，不移动、不重打
`v1.0.2-spec-alignment`、`v1.0.1-audit-polish` 或
`v1.0.0-full-final-version`。该小修使后端 Event Rule severity 在 create /
patch schema 层强制为 `low` / `medium` / `high`，明确 `critical` 只属于
Alert Center `level`；视频上传增加 extension / size / duration / codec
allowlist 校验，并将 `frames` / `tracks` 字段粒度说明为本地 prototype 的
metadata / artifact-compatible 边界。

当前项目仍是本地开发和验证口径，不是生产部署版、production IAM、生产级实时监控或交通执法系统。

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
- Full Stage 3CD Event / Alert / Review DB lifecycle：EventEvidence、RuleExecution、Alert status transitions、Review action audit trail、false-negative DB records 和 event-rules-only rule rerun task / rerun event rows 已接入 DB-first / artifact fallback；完整视频级 rerun 不在本阶段。
- Full Stage 3EF Bad Case / Evaluation DB workflow：Bad Case list/detail/create/update/filter/summary、from-review、from-failed-case、Evaluation dataset/result、failed cases persistence 和 `run_evals.py --write-db` 已接入 DB-first / artifact fallback。
- Full Stage 4AB Trajectory / Event Rules：TrajectoryEngine 已输出 `zone_history`、`lane_relation`、`line_crossings`、dwell/speed/moving_angle/direction consistency 和 center / bottom-center 策略；wrong_way、illegal_parking、danger_zone、pedestrian_lane、congestion、flow_counting 六类规则已补齐 final behavior；速度仍是像素级估计。
- Full Stage 4CD Detection / Tracking benchmark：已实现 IoU、按 class matching、precision、recall、VOC-style single-IoU AP/mAP、per-class AP、frame-level tracking association、IDF1、MOTA、ID switch、track lost、insufficient-data handling，并可写入 DB-backed `evaluation_results`；ID switch / track lost 可输出 Evaluation failed cases 供 Bad Case 转换；该实现不是 COCO official mAP 或 TrackEval official implementation。
- Full Stage 4E Regression Evaluation：已实现 status-based deterministic replay、stored rule replay fixture、per-case regression result、failed regression cases、`regression_pass_rate`、fixed / reopened / failed counts、DB-backed evaluation result persistence 和 CLI/API config 透传；`apply_updates=false` 为默认策略，完整视频级 rerun 不在本阶段。
- Full Stage 5AB ZoneEditor UI：已将 ZoneEditor 从 placeholder 改为真实交互组件，支持 polygon、direction line、counting line 绘制，DB-backed zones / event_rules 保存、更新、删除、读取回显，enabled/version 展示，基础 loading/error/empty 状态和前端 utility tests。
- Full Stage 5CD Video Overlay / EventTimeline：DetectionOverlay、TrackOverlay 和 Zone overlay 已不再是 placeholder；AnalysisDetailPage 已接入 detections、tracks、trajectory_points、zones 和 events 数据叠加展示；EventTimeline 支持过滤、选中和点击事件跳转到对应 timestamp。
- Full Stage 5E Review UX + Evaluation UI：ReviewDrawer 支持 confirm / false_positive / false_negative / ignore / resolve、comments、Review -> Bad Case 和 rule rerun request；Evaluation Center 支持 dataset/run/type selector、result cards、detail JSON、failed cases table、failed-case -> Bad Case、regression summary 和边界标签。
- Full Stage 6AB Report Center：已新增 `/api/reports` run list / summary / JSON export / CSV export，支持 events、alerts、flow_counts、zone_statistics、bad_cases、evaluation_results 六类导出；前端新增 Report Center 页面、run selector、summary cards、CSV download、JSON preview/download、loading/error/empty 状态和非执法边界提示。
- Full Stage 6CD Report Export：已新增 `/api/reports/{run_id}/export.pdf`、`/api/reports/{run_id}/bundle`、keyframe summary、annotated video artifact reference、前端 PDF download 和 bundle / visual artifact summary panel；PDF 与 bundle 均不写入仓库，不复制大视频或图片。
- Full Stage 7AB Camera / Realtime Preview：已新增 DB-backed Cameras API、`upload` / `rtsp` / `file` / `mock` source_type、enable / disable、`stream_url` masking、mock stream preview、local file smoke-level preview、RTSP no-connect preview、recent frames / events / alerts bounded cache、`processing_tasks.mode=realtime_process` linkage、Camera Center 最小前端页面、后端与前端测试和文档。该阶段不是 production realtime monitoring。
- Full Stage 7CD Security / Audit / Ops：已新增 `X-SmartTraffic-Actor` / `X-SmartTraffic-Role` minimal identity、`SMARTTRAFFIC_AUTH_MODE=permissive|strict`、strict-mode preview permission guard、关键写操作 actor propagation、structured audit logging、标准错误响应、request id logging、`/health/ready` DB readiness、env/docs hardening 和测试。该阶段不是 production IAM。
- Full Final Audit / Docs Consistency：对照执行手册 26.1-26.14
  完成文档一致性审计，修正 README/docs/API/database/evaluation/realtime/reporting/security
  口径，并新增 `docs/final_acceptance_checklist.md`。
- v1.0.1 Audit Polish：修复 v1.0.0 后审计缺口，包括 AlertPanel /
  EventTable 真实组件接入、DB-backed processing task list、detector/tracker
  `model_runs` business writes，以及 Stage 6 historical / archived 文档标记。
- v1.0.2 Spec Alignment：修复 run-level alerts DB-first 缺口，并统一 event
  rule severity 为 `low` / `medium` / `high`；不移动 v1.0.1 或 v1.0.0 tag。
- v1.0.3 Final Hardening：后端 Event Rule severity validation、视频上传
  extension / size / duration / codec validation，以及 `frames` / `tracks`
  字段粒度边界已补齐；不移动 v1.0.2、v1.0.1 或 v1.0.0 tag。
- Stage 9AB final pre-delivery audit and documentation closeout。
- Stage 9CD 小型 demo/sample config、toy expected annotations、seed script、Makefile 和环境命令收口。
- Stage 9EF final acceptance and final tag preparation。
- pytest、frontend build、Node utility tests、danger check 和文档化自查命令。

## 3. 未完成边界

- PostgreSQL production deployment 和生产级 migration operations。
- COCO official mAP / public dataset benchmark。
- TrackEval official IDF1 / MOTA benchmark。
- Real dataset benchmark。
- Complete video-level Bad Case rerun pipeline；当前是 deterministic replay / rule replay。
- Production-grade evaluation platform。
- Production realtime streams、production IAM、central audit storage、Permissions / multi-user audit 和 deployment hardening。
- Full Stage 8CD final acceptance 和 `v1.0.0-full-final-version` tag。
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

## 5. Final Acceptance / Tag 状态

Final acceptance 已用于确认当前 main 作为 local delivery baseline：

- 运行后端全量测试、前端测试、前端 build、`docker compose config`、`git diff --check` 和 `scripts/danger_check.py`。
- 扫描 tracked forbidden files、敏感词、大文件、生成结果、视频、模型权重、cache、dist 和 node_modules。
- 确认 README、API reference、architecture、database schema、evaluation、demo plan 和 final delivery plan 一致。
- 确认旧 tag 未移动。
- 最终 annotated tag 为 `v1.0.0-smarttraffic-final-local-delivery`。
- 后续 README/docs/spec completion commits 不移动、不重打该 tag，除非用户明确要求新的版本标签。

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
