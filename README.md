# SmartTraffic 智慧交通事件检测系统

## 项目简介

SmartTraffic 是一个基于 YOLOv8、DeepSORT / mock tracker、Trajectory Engine、Event Engine、artifact-based Alert Center MVP、FastAPI、React 和本地结果产物管理的智慧交通视频分析项目。

当前项目严格按 `docs/SmartTraffic_最终版项目开发执行手册.md` 对齐：Stage 1-4 已完成，Stage 5 已完成 artifact-based / in-memory MVP，Stage 6B/6C 已完成 artifact-based run manifest、artifact index、`flow_counts.json` 和 `zone_statistics.json` MVP。当前实现仍不是数据库最终版，也不代表 Review Center、Bad Case、Evaluation Center 已完成。

当前 Alert Center MVP 支持 `new`、`acknowledged`、`resolved` 和 `ignored` 基础状态流转；这些状态写回本地 alert artifacts，不是数据库持久化生命周期管理。

当前可验证的本地 artifacts 生成和查询闭环是：

```text
video upload
-> metadata extraction
-> YOLOv8 detection
-> DeepSORT / mock tracking
-> Trajectory Engine
-> Event Engine
-> event artifacts
-> traffic statistics artifacts
-> Alert Service
-> alert artifacts
-> run artifacts
-> FastAPI / React display
```

目前支持视频上传、视频元数据读取、YOLOv8 检测、deterministic dry-run 检测、DeepSORT adapter / mock tracking、多目标跟踪结果导出、Trajectory Engine 轨迹点生成、六类事件规则回调、event artifacts、traffic statistics artifacts、alert artifacts、`run_id` 结果目录、前端最小工作台和基础 API。

当前 `POST /api/videos/{video_id}/process` 在 `mode=detection_tracking_trajectory` 下会先运行 detection / tracking / trajectory，然后自动调用 EventService、Stage 6C traffic statistics writer 和 AlertService 写入 event / statistics / alert artifacts。旧请求不传 `event_rules` / `zones` 时会生成稳定的空 event / statistics / alert artifacts，不伪造事件。

本项目当前不是正式交通执法系统，输出结果不作为正式交通执法依据。模型权重、上传视频和运行结果均作为本地资产管理，不进入 Git。

## 技术栈

- Backend: FastAPI, Pydantic, Uvicorn
- CV: YOLOv8 / Ultralytics optional, OpenCV, NumPy
- Tracking: DeepSORT adapter / deterministic mock tracker
- Trajectory: geometry utilities, trajectory features, TrajectoryEngine
- Events: EventEngine callback framework, event contracts, event artifacts
- Alerts: artifact-based Alert Center MVP, alert generation, query and status transitions
- Frontend: React, TypeScript, Vite
- Test: pytest, Vite build
- Storage: local videos and artifact-based run results, Git-ignored
- Deployment skeleton: Docker Compose / local development

## 目录结构

```text
backend/        FastAPI 后端、检测、跟踪、处理服务
frontend/       React + TypeScript 工作台
docs/           阶段文档、架构说明和 API 文档
evals/          评测相关目录占位
samples/        示例资源目录，避免提交大视频
results/        本地 run 产物目录，真实结果文件不提交
local_models/   本地模型权重目录，真实权重不提交
local_videos/   本地上传/测试视频目录，真实视频不提交
scripts/        项目辅助脚本
```

`results/traffic_analysis/` 用于保存每次处理的 `run_id` 结果目录。`local_models/`、`local_videos/` 和真实运行结果均被 `.gitignore` 排除，只保留必要的 `.gitkeep`。

## 本地运行

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

### Docker Compose

```bash
docker compose up
```

当前 Docker Compose 主要用于本地开发骨架，不代表可用于生产环境。

## 环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

重要环境变量类别：

- `SMARTTRAFFIC_RESULTS_DIR`
- `SMARTTRAFFIC_LOCAL_VIDEOS_DIR`
- `SMARTTRAFFIC_LOCAL_MODELS_DIR`
- `YOLO_MODEL_PATH`
- `YOLO_DRY_RUN`
- `YOLO_CONF_THRESHOLD`
- `YOLO_IOU_THRESHOLD`
- `YOLO_DEVICE`
- `DEEPSORT_DRY_RUN`

默认 dry-run 可以不依赖真实模型权重。真实 YOLOv8 推理需要配置本地模型权重路径，例如 `local_models/best.pt`。`.env` 不进入 Git。

## 当前阶段完成内容

当前状态：

- Stage 1 Project Bootstrap completed
- Stage 2 YOLOv8 Detection completed
- Stage 3 Multi-object Tracking completed
- Stage 4 Trajectory Engine completed
- Stage 5 Event / Alert artifact-based MVP completed
- Stage 6B Run manifest / artifact index completed
- Stage 6C Traffic statistics artifacts MVP completed
- Zone / Event Rule configuration API MVP, Event Evidence / Rule Execution artifacts, and Alert Center status workflow implemented

`v0.5.0-event-alert-minimal` is an earlier minimal Event / Alert milestone tag and should not be moved to newer commits.

### 阶段一：项目骨架与视频管理初始化

- 创建 SmartTraffic 项目结构
- FastAPI 后端骨架
- React + Vite 前端骨架
- 基础 `docs` / `evals` / `scripts` / `results` / `local_models` / `local_videos` 目录
- `.gitignore` / `.env.example` / Docker Compose / Makefile
- `GET /health`
- 基础视频 API 骨架
- Traffic Analysis run 目录结构
- pytest / frontend build 基础检查
- GitHub 远程仓库连接和首次 push

对应提交：

```text
3de2678 chore: verify stage 1 project initialization
```

### 阶段二：YOLOv8 检测接入

- `YoloDetector` 封装
- 支持 dry-run detection
- 支持 optional Ultralytics YOLOv8 真实推理
- 视频帧读取与 metadata extraction
- Detection Service
- `detections.csv`
- `detections.jsonl`
- `detection_summary.json`
- 可选 `detection_preview.mp4`
- `POST /api/videos/{video_id}/process` detection_only
- `GET /api/analysis-runs/{run_id}/detections`
- 前端最小上传、触发检测、查看检测摘要
- 阶段二测试和文档

对应提交：

```text
375ae74 feat: implement stage 2 YOLOv8 detection pipeline
```

### 阶段三：DeepSORT / mock tracking 多目标跟踪接入

- `DeepSortTracker` adapter
- deterministic mock tracker
- optional `deep-sort-realtime` fallback 设计
- 基于 detections 生成 tracks
- 稳定 `track_id` contract
- Tracking Service
- `tracks.csv`
- `tracks.jsonl`
- `tracking_summary.json`
- 可选 `tracking_preview.mp4`
- `mode=detection_tracking`
- `GET /api/analysis-runs/{run_id}/tracks`
- 前端最小 tracking summary 和 tracks 展示
- 阶段三测试和文档

对应提交：

```text
0475fcb feat: implement stage 3 DeepSORT tracking pipeline
```

### 阶段四：Trajectory Engine 轨迹分析

- Geometry 工具：
  - point in polygon
  - bbox center / bottom-center
  - segment intersection
  - line crossing direction
  - vector angle
  - angle difference
- Trajectory Features：
  - `speed_px_per_frame`
  - `speed_px_per_second`
  - `direction_vector`
  - `moving_angle`
  - `dwell_time_ms`
  - `track_length`
- TrajectoryEngine：
  - 内存 track state cache
  - 单帧 tracks -> trajectory_points
  - `track_length` / `last_seen` / state summary
- Trajectory artifacts：
  - `trajectory_points.csv`
  - `trajectory_points.jsonl`
  - `trajectory_summary.json`
- Trajectory Service：
  - detection -> tracking -> trajectory pipeline
  - `mode=detection_tracking_trajectory`
  - metadata `stage=stage_4_trajectory_engine`
- API：
  - `GET /api/analysis-runs/{run_id}/trajectory-points`
- Frontend：
  - VideoCenter 支持 `detection_tracking_trajectory`
  - AnalysisDetail 展示 trajectory summary / rows / frames
  - 支持 `track_id` filter

`speed_px_per_second` 当前是基于 timestamp 或 fps 的像素级速度估算，不是真实世界 m/s 或 km/h。

对应提交：

```text
47bd3b4 feat: add trajectory geometry utilities
b6b4315 feat: add trajectory feature utilities
ac52c5b feat: add trajectory engine state cache
23dd0e0 feat: add trajectory artifact writer outputs
f1f72e8 feat: add trajectory service pipeline
dffaf02 feat: add trajectory points query api
1a9dad8 feat: add minimal trajectory frontend view
```

### 阶段五：Event Engine / Alert Center artifact-based MVP

当前阶段五已完成 artifact-based / in-memory MVP。已实现部分包括 Zone / Event Rule 配置 API MVP、Event contract、六个规则回调、event artifacts、alert artifacts、Alert Center 基础查询与状态流转，以及 process pipeline 中 detection / tracking / trajectory / event / alert artifact generation 的直接串联。阶段五仍不是数据库最终版，zone/rule 和 alert 状态均为本地 artifact / 内存边界。

Implemented:

- Event contract / evidence / rule execution records
- Zone / Event Rule 配置 API MVP：
  - `POST /api/zones`
  - `GET /api/zones`
  - `PATCH /api/zones/{zone_id}`
  - `DELETE /api/zones/{zone_id}`
  - `POST /api/event-rules`
  - `GET /api/event-rules`
  - `PATCH /api/event-rules/{rule_id}`
  - `DELETE /api/event-rules/{rule_id}`
- Event artifacts：
  - `events.jsonl`
  - `event_evidence.jsonl`
  - `rule_executions.jsonl`
  - `event_summary.json`
- Event Evidence 已补充 rule parameters、trigger reason、trajectory features 和 snapshot fallback 信息
- Rule Execution 已稳定记录 matched / not_matched / skipped / error
- EventEngine callback framework
- 已实现六类事件规则回调：
  - `danger_zone_intrusion`
  - `pedestrian_in_vehicle_lane`
  - `illegal_parking`
  - `wrong_way_driving`
  - `flow_counting`
  - `congestion`
- EventService：基于已有 `trajectory_points.jsonl`、rules 和 zones 生成 event artifacts
- Process integration：`mode=detection_tracking_trajectory` 完成 trajectory 后自动运行 EventService；未提供 rules / zones 时写出空 event artifacts
- Event query API：`GET /api/analysis-runs/{run_id}/events`
- Alert contract
- AlertService：基于已有 `events.jsonl` 生成 alert artifacts
- Process integration：EventService 完成后自动运行 AlertService；空 events 会写出空 alert artifacts
- Alert artifacts：
  - `alerts.jsonl`
  - `alert_summary.json`
- Alert generate/query/status API：
  - `POST /api/analysis-runs/{run_id}/alerts/generate`
  - `GET /api/analysis-runs/{run_id}/alerts`
  - `GET /api/alerts`
  - `GET /api/alerts/{alert_id}`
  - `PATCH /api/alerts/{alert_id}/acknowledge`
  - `PATCH /api/alerts/{alert_id}/resolve`
  - `PATCH /api/alerts/{alert_id}/ignore`
- Analysis Detail 最小 event / alert table 展示
- Alert Center 最小页面：支持 run/status/level 过滤，以及 acknowledge / resolve / ignore
- Alert 状态流转：支持 `new` / `acknowledged` / `resolved` / `ignored`

Not implemented yet:

- database-backed zone/rule config persistence
- database-backed alert persistence
- database-backed Traffic Analysis result index
- Review / Bad Case / Evaluation
- Database implementation / persistence

Event/Alert query endpoints are artifact-based MVP endpoints. They are not a full database-backed result center.

当前事件判断基于像素级轨迹特征、zone polygon 和规则阈值。`illegal_parking` 是视频分析事件，不是正式执法级违停结论。

`wrong_way_driving` 基于 `vehicle_lane` zone、`moving_angle`、`allowed_angle`、`angle_tolerance` 和 `min_speed_px_per_frame` 判断明显反向行驶。它使用 strict wrong-way 判断：`angle_diff = angle_difference(moving_angle, allowed_angle)`，并要求 `angle_diff >= 180 - angle_tolerance`。横向运动不会被误判为 wrong-way。该规则不是正式执法级方向判断，没有真实世界方向标定，也没有连续帧 wrong-way counter；`min_wrong_way_frames > 1` 当前不支持。

`flow_counting` 是 Stage 5 EventEngine rule。它通过当前点和 previous point 判断 track segment 是否穿越 `rule.parameters.line` counting line，使用 `evidence_type=line_crossing`，支持 `direction=any / positive / negative` 和 `count_once_per_track`。Stage 6C 会基于生成的 `flow_counting` events / evidence 写出 artifact-based `flow_counts.json`，并提供 `GET /api/analysis-runs/{run_id}/flow-counts` 读取入口。当前仍不提供前端流量图表、持久化 counting line 配置、数据库聚合或真实世界流量标定。

`congestion` 是 Stage 5 aggregate EventEngine rule。它通过 aggregate callback 每帧按 zone 聚合车辆数量和平均像素速度，使用 `event_type=congestion`、`evidence_type=zone_statistics`、`rule_mode=aggregate` 和 `track_id=None`，基于 `vehicle_count`、`avg_speed_px_per_frame` 与 `min_congestion_frames` 生成事件。Stage 6C 会基于 trajectory zone 信息和 congestion evidence 写出 artifact-based `zone_statistics.json`，并提供 `GET /api/analysis-runs/{run_id}/zone-statistics` 读取入口。当前仍不提供前端拥堵图表、数据库区域统计持久化、真实世界拥堵标定或执法判断。

对应提交：

```text
badc3d4 feat: add event artifact contracts
33ad73f feat: add minimal event engine framework
733d767 feat: add danger zone intrusion rule
3b52ea9 feat: add pedestrian lane intrusion rule
e6c24c6 feat: add illegal parking rule
3b8b47d feat: add event query pipeline
d4e1f13 feat: add minimal alert center
a8ea862 feat: add wrong way driving rule
01d6c3d feat: add flow counting rule
bddcd93 feat: add congestion rule
```

## API

当前主要 API：

- `GET /health`
- `POST /api/videos/upload`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `POST /api/videos/{video_id}/process`
- `GET /api/videos/{video_id}/status`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/manifest`
- `GET /api/analysis-runs/{run_id}/detections`
- `GET /api/analysis-runs/{run_id}/tracks`
- `GET /api/analysis-runs/{run_id}/trajectory-points`
- `GET /api/analysis-runs/{run_id}/events`
- `GET /api/analysis-runs/{run_id}/flow-counts`
- `GET /api/analysis-runs/{run_id}/zone-statistics`
- `POST /api/analysis-runs/{run_id}/alerts/generate`
- `GET /api/analysis-runs/{run_id}/alerts`
- `GET /api/alerts`
- `GET /api/alerts/{alert_id}`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/{alert_id}/resolve`
- `PATCH /api/alerts/{alert_id}/ignore`

`POST /api/videos/{video_id}/process` 当前支持：

- `mode=detection_only`
- `mode=detection_tracking`
- `mode=detection_tracking_trajectory`
- `detector_dry_run`
- `tracker_dry_run`
- `frame_stride`
- `max_frames`
- `conf_threshold`
- `iou_threshold`
- `write_preview`
- `direction_window`
- `dwell_speed_threshold`
- `max_history_points`
- `event_rules`
- `zones`
- `run_events`
- `generate_alerts`
- `record_not_matched`

当前 process API 在 `mode=detection_tracking_trajectory` 下会自动生成 event / traffic statistics / alert artifacts，并通过 `GET /api/analysis-runs/{run_id}/events`、`GET /api/analysis-runs/{run_id}/flow-counts`、`GET /api/analysis-runs/{run_id}/zone-statistics` 与 `GET /api/analysis-runs/{run_id}/alerts` 查询。process response 仍以原有处理摘要为主，不直接展开完整 event / statistics / alert 明细。

## 结果产物

当前本地处理和后续 Event / Alert artifact 生成后，默认结果目录可能包含：

```text
results/traffic_analysis/<run_id>/
  metadata.json
  manifest.json
  artifact_index.json
  detections.csv
  detections.jsonl
  detection_summary.json
  tracks.csv
  tracks.jsonl
  tracking_summary.json
  trajectory_points.csv
  trajectory_points.jsonl
  trajectory_summary.json
  events.jsonl
  event_evidence.jsonl
  rule_executions.jsonl
  event_summary.json
  flow_counts.json
  zone_statistics.json
  alerts.jsonl
  alert_summary.json
  detection_preview.mp4   # only when requested
  tracking_preview.mp4    # only when requested
  keyframes/              # directory reserved; event snapshots are not generated yet
```

Stage 6B adds `manifest.json` and `artifact_index.json` for each run so callers can distinguish available, missing, planned, empty, and error artifact states. Stage 6C adds artifact-based `flow_counts.json` and `zone_statistics.json` plus read APIs. EventService 和 AlertService 基于上述 local artifacts 工作。当前 Traffic Analysis Center 是 artifact-based run result query，不是完整数据库结果中心。真实运行产物不提交到 Git。

The `v0.5.0-event-alert-minimal` tag marks an earlier minimal Event / Alert milestone only.

## 当前边界

当前尚未实现：

- frontend flow statistics chart
- frontend congestion chart
- Review Center 真实逻辑
- Bad Case Center 真实逻辑
- Evaluation Center 完整评测
- 数据库持久化 Zone / Event Rule / Alert 状态
- DB-backed result index
- keyframe snapshot generation
- final annotated_video pipeline
- video overlay
- 正式实时流处理
- 真实世界速度标定；当前 `speed_px_per_second` 不是 m/s 或 km/h
- law-enforcement-grade violation judgement
- 生产级权限、安全和监控

项目输出不作为正式交通执法依据。

## 安全与数据策略

- 不提交 `.env`
- 不提交 API key / token / secret
- 不提交模型权重
- 不提交大视频
- 不提交上传视频
- 不提交 `results/` 真实运行产物
- 不提交 `local_models/` 和 `local_videos/` 真实内容
- `results/traffic_analysis/.gitkeep` 可以保留
- 模型权重和视频只在本地使用
- 项目输出不作为正式交通执法依据

## 文档索引

- `docs/api_reference.md`
- `docs/migration_from_yolov8.md`
- `docs/stage2_yolov8_detection.md`
- `docs/stage3_deepsort_tracking.md`
- `docs/stage4_trajectory_engine.md`
- `docs/stage5_event_alert_pipeline.md`
- `docs/architecture.md`
- `docs/database_schema.md`

## 自查命令

后端检查：

```bash
cd backend
pytest -q
python -m compileall app
```

前端检查：

```bash
cd ../frontend
npm install
npm run build
```

Git 和格式检查：

```bash
cd ..
git status --short --branch
git diff --check
```

大文件检查：

```bash
find . -type file -size +50M \
  -not -path "./.git/*" \
  -not -path "./frontend/node_modules/*" \
  -not -path "./backend/.venv/*"
```

敏感词检查：

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules \
  -E "OPENAI_API_KEY|api_key|secret|password|token|sk-|ghp_|github_pat_" .
```
