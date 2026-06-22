# SmartTraffic 智慧交通事件检测系统｜最终版项目开发执行手册

> 项目定位：SmartTraffic 是基于 **YOLOv8 + DeepSORT + Trajectory Engine + Event Engine + Traffic Analysis Center + Review Center + Evaluation Center + FastAPI + React + Database** 的智慧交通事件检测平台。  
> 本手册面向正式项目开发过程，描述产品边界、技术架构、模块职责、数据库、处理流程、事件规则、结果管理、告警、复核、Bad Case、评测体系和最终交付验收标准。

---

## 0. 项目总判断

SmartTraffic 应被定义为一个“智慧交通事件检测平台”，而不是只展示检测框的视频目标检测 Demo。系统的核心价值不止在于识别车辆和行人，而在于把视频输入、目标检测、多目标跟踪、轨迹分析、事件规则判断、区域划线、告警生成、结果分析、人工复核、Bad Case 和评测回归串成一条可运行、可解释、可复查、可评测的工程链路。

项目应围绕六类能力展开：

| 能力层级 | 系统目标 | 工程重点 |
| --- | --- | --- |
| 感知层 | 检测车辆、行人和其他交通参与者 | YOLOv8、bbox、class、confidence、frame_index |
| 时序层 | 将单帧检测关联为连续目标轨迹 | DeepSORT、track_id、ID Switch、Track Lost |
| 轨迹层 | 计算速度、方向、停留时间、区域关系和穿线行为 | Trajectory Engine、几何计算、时间窗口 |
| 事件层 | 基于轨迹和规则判断交通事件 | Event Engine、区域、方向线、阈值、冷却时间 |
| 结果层 | 统一管理一次视频分析的全部产物 | Traffic Analysis Center、run_id、结果索引 |
| 质量层 | 复核事件、记录错误、评测指标和回归 | Review Center、Bad Case、Evaluation Center |

系统设计包含以下判断：

- YOLOv8 只负责目标检测，不负责交通事件判断。
- DeepSORT 负责目标身份连续性，为轨迹和事件判断提供 `track_id`。
- Trajectory Engine 负责把目标位置序列转化为速度、方向、停留时间和区域关系。
- Event Engine 负责根据可配置规则生成事件，不直接做模型推理。
- Traffic Analysis Center 是结果管理层，不做模型推理，也不做事件判断。
- Alert Center 负责把事件转化为可处理告警，并管理告警状态。
- Review Center 保留人工确认、误报标记、漏报补充、备注和审计留痕。
- Evaluation Center 覆盖检测、跟踪、轨迹、事件、流量统计和 Bad Case 回归评测。

项目开发应坚持四个原则：

1. 模块边界清楚：检测、跟踪、轨迹、事件、结果管理、告警、复核、评测各自承担明确职责。
2. 事件可解释：每个事件都要保存触发区域、轨迹点、速度、方向角、阈值、帧号和截图等证据。
3. 结果可复查：事件结果能回到视频帧、track_id、规则配置、区域配置和处理任务。
4. 评测可回归：误报、漏报、ID Switch、轨迹丢失、规则错误和区域配置错误要进入 Bad Case 与回归评测。

---

## 1. 项目总定位

### 1.1 项目名称

**SmartTraffic 智慧交通事件检测系统**

### 1.2 一句话定位

SmartTraffic 是面向城市道路、园区道路、校园道路、停车场和出入口视频分析场景的智慧交通事件检测平台，基于 YOLOv8、DeepSORT、Trajectory Engine、Event Engine、Traffic Analysis Center、Review Center、Evaluation Center、FastAPI、React 和数据库，支持视频管理、离线视频处理、可选实时流处理、目标检测、多目标跟踪、轨迹事件判断、区域划线、方向配置、告警、复核、结果导出和评测闭环。

### 1.3 项目边界

本项目要做：

- 管理视频文件、摄像头源、处理任务和分析运行记录。
- 对视频帧执行 YOLOv8 目标检测。
- 对检测结果执行 DeepSORT 多目标跟踪。
- 生成轨迹点、速度、方向、停留时间、区域历史和穿线记录。
- 支持 vehicle_lane、pedestrian_area、no_parking_zone、danger_zone、counting_zone、roi 等区域配置。
- 支持 direction line、allowed_angle、reverse_angle_threshold、counting line 等方向和计数配置。
- 判断车辆逆行、违停、危险区域闯入、行人进入机动车道、拥堵和车流/人流统计事件。
- 将事件转为告警并支持状态处理。
- 统一管理一次视频分析的检测、跟踪、轨迹、事件、告警、统计、关键帧、标注视频和评测产物。
- 支持人工复核、误报标记、漏报补充、Bad Case 记录和回归评测。

本项目不做：

- 不作为正式交通执法依据。
- 不宣称生产部署、客户落地、城市道路治理效果或商业收益。
- 不用单帧检测结果直接代替交通行为判断。
- 不将事件规则硬编码到检测模型中。
- 不用单个标注视频代替检测、跟踪、事件和流量评测。
- 不把大视频、模型权重、批量结果和敏感数据写入公开仓库。

### 1.4 核心链路

```text
video input
  -> YOLOv8 object detection
  -> DeepSORT multi-object tracking
  -> Trajectory Engine
  -> Event Engine
  -> Alert Center
  -> Traffic Analysis Center
  -> Dashboard / Review Center
  -> Evaluation Center + Bad Case loop
```

---

## 2. 真实业务背景

城市道路、园区道路、校园道路、停车场、出入口和路口视频通常用于记录交通状态，但原始视频本身不能直接回答以下问题：

- 某辆车是否逆向行驶。
- 某辆车是否在禁停区域长期停留。
- 行人是否进入机动车道。
- 是否有车辆或行人进入危险区域。
- 某路段是否出现拥堵。
- 单位时间内车辆和行人流量如何变化。

单纯目标检测只能回答“画面中有什么目标”。交通事件需要结合“同一目标是谁”“目标如何移动”“目标在哪个区域”“方向是否符合配置”“停留时间是否超过阈值”“是否穿越计数线”等时序和空间信息。因此系统需要从检测扩展到跟踪、轨迹、规则、告警、复核和评测。

本项目适合使用：

- 公开视频。
- 公开交通数据集。
- 模拟区域配置。
- 自建少量标注样例。

系统输出只作为视频分析结果，不构成正式交通执法依据。所有指标应基于真实运行和评测结果填写。

---

## 3. 目标用户与使用场景

### 3.1 目标用户

| 用户类型 | 核心诉求 |
| --- | --- |
| 交通视频分析人员 | 查看道路视频事件、轨迹和流量统计 |
| 园区/校园安全管理人员 | 识别危险区域闯入、行人进入机动车道和异常停留 |
| 停车场与出入口管理人员 | 分析出入口流量、违停和拥堵状态 |
| 计算机视觉工程人员 | 验证检测、跟踪、轨迹和事件规则效果 |
| 系统管理员 | 管理视频源、区域配置、事件规则和处理任务 |
| 复核人员 | 确认事件、标记误报、补充漏报和维护 Bad Case |

### 3.2 使用场景

| 场景 | 输入 | 输出 |
| --- | --- | --- |
| 城市道路离线分析 | 上传道路视频 | 检测、跟踪、轨迹、事件、流量和报告 |
| 园区道路安全监控 | 上传视频或接入视频源 | 危险区域闯入、违停、行人进入机动车道 |
| 校园道路异常行为分析 | 校园道路视频 | 行人进入机动车道、拥堵、车流统计 |
| 停车场与出入口分析 | 出入口视频 | 车辆流量、方向统计、违停和拥堵 |
| 公开视频评测 | 公开数据或样例视频 | 检测、跟踪、事件和 Bad Case 指标 |
| 可选实时流处理 | RTSP / 本地摄像头 | 实时事件和告警流 |

### 3.3 用户核心诉求

- 上传或接入交通视频。
- 配置区域、方向线、计数线和事件规则。
- 查看检测框、track_id、轨迹线、区域叠加和事件时间轴。
- 查询事件列表、告警状态和流量统计。
- 复核事件结果并沉淀 Bad Case。
- 查看检测、跟踪、轨迹、事件和流量评测指标。

---

## 4. 产品模块设计

### 4.1 模块总览

| 模块 | 核心职责 | 主要输出 |
| --- | --- | --- |
| 视频管理模块 | 上传、存储、预览、元数据读取和处理状态管理 | videos、frames、processing_tasks |
| YOLOv8 检测模块 | 对车辆、行人等目标进行检测 | detections、检测标注帧 |
| DeepSORT 跟踪模块 | 为检测目标分配稳定 track_id | tracks、track states |
| Trajectory Engine | 维护轨迹点和计算轨迹特征 | trajectory_points、track features |
| Event Engine | 基于规则判断交通事件 | events、event_evidence、rule_executions |
| 事件类型设计 | 定义逆行、违停、闯入、行人入机动车道、拥堵和流量统计 | event_type schema |
| 区域划线与方向配置 | 管理 polygon、direction line、counting line 和阈值 | zones、event_rules |
| Traffic Analysis Center | 按 run_id 统一管理全部分析结果 | traffic_analysis_runs、结果目录 |
| Alert Center | 根据事件生成告警并处理状态 | alerts |
| Review Center | 人工确认事件、标记误报/漏报、备注和审计留痕 | review_comments、事件状态 |
| Bad Case Center | 记录错误样例、根因和回归状态 | bad_cases |
| Evaluation Center | 管理检测、跟踪、轨迹、事件、流量和回归评测 | evaluation_datasets、evaluation_results |
| Dashboard | 展示视频、事件、告警、统计和评测 | 前端页面 |
| 报告与导出 | 导出事件、流量、统计、Bad Case 和评测结果 | CSV / JSON / PDF / MP4 |

### 4.2 产品页面

| 页面 | 功能 |
| --- | --- |
| Dashboard | 视频数量、处理状态、事件趋势、告警数、流量统计和评测摘要 |
| Video Center | 上传视频、查看元数据、处理状态、标注视频和结果索引 |
| Analysis Detail | 视频播放、检测框、轨迹线、区域叠加、事件时间轴和关键帧 |
| Zone & Rule Config | 绘制区域、方向线、计数线，配置事件规则 |
| Alert Center | 查询告警、确认告警、关闭告警和查看关联事件 |
| Review Center | 复核事件、标记误报/漏报、补充备注和关联 Bad Case |
| Bad Case Center | 查看错误案例、错误类型、标签、截图和修复状态 |
| Evaluation Center | 展示检测、跟踪、轨迹、事件、流量和回归评测 |
| Report Center | 导出事件、流量统计、分析摘要、关键帧和标注视频 |

### 4.3 产品主流程

```text
用户上传或选择视频
  -> 创建处理任务
  -> 读取视频元数据
  -> 执行 YOLOv8 检测
  -> 执行 DeepSORT 跟踪
  -> 更新轨迹特征
  -> 执行事件规则
  -> 生成事件和告警
  -> Traffic Analysis Center 统一索引结果
  -> Dashboard 展示
  -> Review Center 复核
  -> Bad Case 与 Evaluation Center 迭代
```

---

## 5. 技术架构

### 5.1 系统分层

```text
Frontend
React / TypeScript / Video + Canvas Overlay / Charts
        |
FastAPI Backend
Video API / Processing API / Event API / Alert API / Review API / Evaluation API
        |
Processing Services
Frame Extractor / YOLOv8 Detector / DeepSORT Tracker
Trajectory Engine / Event Engine / Result Writer
        |
Result Management
Traffic Analysis Center / Report Export / Keyframe Manager
        |
Data Layer
Database / Local File Storage / Result Artifacts / Evaluation Datasets
```

### 5.2 推荐技术栈

| 层级 | 技术 | 说明 |
| --- | --- | --- |
| 后端 API | Python, FastAPI, Pydantic, SQLAlchemy | API、任务、结果查询和复核 |
| CV 推理 | YOLOv8, PyTorch, OpenCV | 目标检测和视频处理 |
| 多目标跟踪 | DeepSORT | 目标身份保持和轨迹生成 |
| 轨迹计算 | NumPy, OpenCV geometry utilities | 速度、方向、区域关系和穿线 |
| 数据库 | PostgreSQL / SQLite prototype | 结构化结果、规则、复核和评测 |
| 文件存储 | local storage / object storage | 原视频、标注视频、关键帧、CSV/JSON |
| 任务处理 | FastAPI BackgroundTasks / Celery | 离线处理和长任务 |
| 前端 | React, TypeScript, Vite | Dashboard 和分析工作台 |
| 可视化 | Canvas / SVG Overlay, ECharts / Recharts | 视频叠加、趋势和统计图 |
| 部署 | Docker Compose | 本地复现 |

### 5.3 核心数据流

```text
video_file
  -> metadata extraction
  -> frames
  -> detections
  -> tracks
  -> trajectory_points
  -> events
  -> event_evidence
  -> alerts
  -> traffic_analysis_run artifacts
```

### 5.4 模块间契约

| 上游 | 下游 | 契约 |
| --- | --- | --- |
| Video Manager | Processing Task | video_id、run_id、processing params |
| YOLOv8 Detector | DeepSORT Tracker | frame_index、bbox、class_name、confidence |
| DeepSORT Tracker | Trajectory Engine | track_id、bbox、center、state、timestamp |
| Trajectory Engine | Event Engine | speed、moving_angle、dwell_time、zone_history、lane_relation |
| Event Engine | Alert Center | event_type、severity、evidence、snapshot_path |
| Event Engine | Traffic Analysis Center | events、event_evidence、rule_executions |
| Review Center | Bad Case Center | reviewed event、case_type、expected_result、actual_result |
| Evaluation Center | Traffic Analysis Center | metrics、evaluation artifacts、failed cases |

### 5.5 工程规则

- API 层不直接调用 YOLOv8 或 DeepSORT，推理逻辑放在 Processing Services。
- 模型路径、置信度阈值、NMS 阈值、抽帧间隔、跟踪参数和事件阈值必须配置化。
- 事件规则不能硬编码到检测模块。
- 每个事件必须保存证据，至少包含 track_id、frame_index、timestamp、zone_id、规则参数和触发原因。
- 长视频处理使用任务状态记录，避免请求阻塞。
- 原视频、标注视频、批量结果和模型权重默认不提交到 Git。

---

## 6. GitHub目录结构

推荐目录结构如下：

```text
smarttraffic/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── docs/
│   ├── SmartTraffic_最终版项目开发执行手册.md
│   ├── api_reference.md
│   ├── architecture.md
│   ├── database_schema.md
│   ├── event_rules.md
│   ├── zone_config.md
│   ├── evaluation.md
│   └── screenshots/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── videos.py
│   │   │   ├── processing.py
│   │   │   ├── detections.py
│   │   │   ├── tracks.py
│   │   │   ├── trajectories.py
│   │   │   ├── events.py
│   │   │   ├── alerts.py
│   │   │   ├── zones.py
│   │   │   ├── analysis_runs.py
│   │   │   ├── review.py
│   │   │   ├── bad_cases.py
│   │   │   └── evaluation.py
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── services/
│   │   │   ├── video_service.py
│   │   │   ├── processing_service.py
│   │   │   ├── detection_service.py
│   │   │   ├── tracking_service.py
│   │   │   ├── trajectory_service.py
│   │   │   ├── event_service.py
│   │   │   ├── alert_service.py
│   │   │   ├── traffic_analysis_service.py
│   │   │   ├── review_service.py
│   │   │   ├── bad_case_service.py
│   │   │   └── evaluation_service.py
│   │   ├── cv/
│   │   │   ├── yolo_detector.py
│   │   │   ├── deepsort_tracker.py
│   │   │   ├── frame_reader.py
│   │   │   └── video_writer.py
│   │   ├── trajectory/
│   │   │   ├── engine.py
│   │   │   ├── geometry.py
│   │   │   └── features.py
│   │   ├── events/
│   │   │   ├── engine.py
│   │   │   ├── rules.py
│   │   │   ├── dedup.py
│   │   │   └── evidence.py
│   │   ├── analysis/
│   │   │   ├── run_index.py
│   │   │   ├── artifact_writer.py
│   │   │   └── export.py
│   │   ├── evaluation/
│   │   └── db/
│   ├── tests/
│   │   ├── test_video_api.py
│   │   ├── test_trajectory_geometry.py
│   │   ├── test_event_rules.py
│   │   ├── test_flow_counting.py
│   │   ├── test_review_flow.py
│   │   └── test_evaluation.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── store/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
├── evals/
│   ├── datasets/
│   ├── expected/
│   ├── results/
│   └── scripts/
├── samples/
│   └── videos/
├── results/
│   └── traffic_analysis/
├── local_models/
├── local_videos/
└── scripts/
    ├── seed_demo_data.py
    ├── run_evals.py
    └── danger_check.py
```

目录设计说明：

- `backend/app/cv/` 保存检测、跟踪和视频读写。
- `backend/app/trajectory/` 保存轨迹特征和几何计算。
- `backend/app/events/` 保存事件规则、去重和证据构造。
- `backend/app/analysis/` 保存 Traffic Analysis Center 的结果索引和导出。
- `evals/` 保存评测数据、预期输出和评测报告。
- `local_models/`、`local_videos/`、`results/traffic_analysis/` 为本地资产目录，默认不提交。

---

## 7. FastAPI后端结构

### 7.1 后端职责

FastAPI 后端负责：

- 视频上传、元数据读取、处理任务和结果查询。
- 检测、跟踪、轨迹、事件和告警服务编排。
- 区域划线、方向线、计数线和事件规则管理。
- Traffic Analysis Center 结果索引、关键帧、标注视频和导出。
- Review Center 事件复核、状态更新和审计记录。
- Bad Case 与 Evaluation Center 数据管理。
- 为 React 前端提供稳定 JSON API。

### 7.2 后端分层

| 层级 | 职责 |
| --- | --- |
| api | HTTP 路由、参数校验、响应封装 |
| schemas | Pydantic 请求、响应和结果 Schema |
| services | 业务流程编排 |
| repositories | 数据库读写 |
| cv | YOLOv8、DeepSORT、视频读写 |
| trajectory | 轨迹缓存、特征计算和几何工具 |
| events | 事件规则、去重、证据构造 |
| analysis | run_id 结果索引、产物写入和导出 |
| evaluation | 检测、跟踪、轨迹、事件和流量评测 |
| core | 配置、日志、错误、安全和路径管理 |

### 7.3 API 规划

基础接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/api/config` | 查询前端配置 |

视频 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/videos/upload` | 上传视频 |
| GET | `/api/videos` | 查询视频列表 |
| GET | `/api/videos/{video_id}` | 查询视频详情 |
| POST | `/api/videos/{video_id}/process` | 启动处理 |
| GET | `/api/videos/{video_id}/status` | 查询处理状态 |
| GET | `/api/videos/{video_id}/frames` | 查询帧信息 |

结果 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/analysis-runs/{run_id}` | 查询分析运行详情 |
| GET | `/api/analysis-runs/{run_id}/detections` | 查询检测结果 |
| GET | `/api/analysis-runs/{run_id}/tracks` | 查询跟踪结果 |
| GET | `/api/analysis-runs/{run_id}/trajectory-points` | 查询轨迹点 |
| GET | `/api/analysis-runs/{run_id}/flow-counts` | 查询流量统计 |
| GET | `/api/analysis-runs/{run_id}/zone-statistics` | 查询区域统计 |

事件与告警 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/events` | 查询事件 |
| GET | `/api/events/{event_id}` | 查询事件详情 |
| PATCH | `/api/events/{event_id}/status` | 更新事件状态 |
| GET | `/api/alerts` | 查询告警 |
| PATCH | `/api/alerts/{alert_id}/acknowledge` | 确认告警 |
| PATCH | `/api/alerts/{alert_id}/resolve` | 关闭告警 |

配置 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/zones` | 创建区域 |
| GET | `/api/zones` | 查询区域 |
| PATCH | `/api/zones/{zone_id}` | 更新区域 |
| DELETE | `/api/zones/{zone_id}` | 删除区域 |
| POST | `/api/event-rules` | 创建事件规则 |
| GET | `/api/event-rules` | 查询事件规则 |
| PATCH | `/api/event-rules/{rule_id}` | 更新事件规则 |

复核、Bad Case 与评测 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/review/events` | 查询待复核事件 |
| POST | `/api/review/comments` | 新增复核备注 |
| POST | `/api/events/{event_id}/bad-case` | 关联 Bad Case |
| POST | `/api/bad-cases` | 创建 Bad Case |
| GET | `/api/bad-cases` | 查询 Bad Case |
| POST | `/api/evaluation/run` | 启动评测 |
| GET | `/api/evaluation/results` | 查询评测结果 |

### 7.4 后端工程规则

- 上传视频校验格式、大小、时长和编码。
- 推理处理通过 processing_tasks 记录状态。
- 长任务写入错误信息和失败阶段，便于重试。
- 所有结果按 `video_id` 和 `run_id` 查询。
- 事件状态更新、复核备注和 Bad Case 创建应写审计记录。
- API 不返回底层 traceback，不在日志中输出敏感路径或密钥。

---

## 8. React前端结构

### 8.1 前端职责

React 前端负责视频管理、结果展示、区域配置、事件复核、告警处理、Bad Case 管理和评测查看，不负责执行模型推理、跟踪和事件规则计算。

### 8.2 前端目录

```text
frontend/src/
├── api/
│   ├── client.ts
│   ├── videos.ts
│   ├── analysisRuns.ts
│   ├── events.ts
│   ├── alerts.ts
│   ├── zones.ts
│   ├── review.ts
│   ├── badCases.ts
│   └── evaluation.ts
├── components/
│   ├── VideoPlayerWithOverlay.tsx
│   ├── DetectionOverlay.tsx
│   ├── TrackOverlay.tsx
│   ├── ZoneEditor.tsx
│   ├── DirectionLineEditor.tsx
│   ├── EventTimeline.tsx
│   ├── EventTable.tsx
│   ├── AlertPanel.tsx
│   ├── ReviewDrawer.tsx
│   └── MetricCards.tsx
├── pages/
│   ├── DashboardPage.tsx
│   ├── VideoCenterPage.tsx
│   ├── AnalysisDetailPage.tsx
│   ├── ZoneRuleConfigPage.tsx
│   ├── AlertCenterPage.tsx
│   ├── ReviewCenterPage.tsx
│   ├── BadCaseCenterPage.tsx
│   └── EvaluationCenterPage.tsx
├── store/
├── types/
├── routes/
└── utils/
```

### 8.3 页面设计

| 页面 | 功能 |
| --- | --- |
| DashboardPage | 视频状态、事件趋势、告警数量、流量统计和评测摘要 |
| VideoCenterPage | 上传视频、查看处理任务、标注视频和结果产物 |
| AnalysisDetailPage | 视频播放、检测框、轨迹、区域、事件时间轴和关键帧 |
| ZoneRuleConfigPage | 区域划线、方向线、计数线和事件阈值配置 |
| AlertCenterPage | 告警查询、确认和关闭 |
| ReviewCenterPage | 事件复核、误报标记、漏报补充和备注 |
| BadCaseCenterPage | 错误样例、错误来源、标签和修复状态 |
| EvaluationCenterPage | 检测、跟踪、轨迹、事件、流量和回归评测 |

### 8.4 前端工程规则

- 视频叠加层使用稳定坐标映射，适配不同播放尺寸。
- 事件时间轴点击后跳转到对应时间戳。
- 区域和方向线编辑需要支持保存、回显和版本区分。
- 复核动作必须二次确认，避免误改事件状态。
- 指标图表必须显示数据集名称、运行时间和评测类型。

---

## 9. 数据库设计

### 9.1 设计原则

- `video_id` 是视频维度主索引。
- `run_id` 是一次分析运行主索引。
- `frame_index` 和 `timestamp_ms` 用于还原事件发生位置。
- `track_id` 串联 tracks、trajectory_points、events 和 bad_cases。
- 事件、告警、复核、规则执行和评测都应保留证据。
- 原始视频、标注视频、关键帧和 CSV/JSON 产物存文件路径，结构化索引入库。

### 9.2 videos

用途：存储视频文件和处理状态。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 视频 ID |
| filename | VARCHAR | 原始文件名 |
| file_path | TEXT | 视频路径 |
| output_path | TEXT | 标注视频路径 |
| status | VARCHAR | uploaded / processing / completed / failed |
| fps | FLOAT | 帧率 |
| width | INTEGER | 宽度 |
| height | INTEGER | 高度 |
| duration_seconds | FLOAT | 时长 |
| total_frames | INTEGER | 总帧数 |
| camera_id | FK | 摄像头 |
| process_mode | VARCHAR | offline / realtime |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9.3 cameras

用途：存储摄像头或视频源信息。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 摄像头 ID |
| name | VARCHAR | 名称 |
| location | VARCHAR | 位置 |
| stream_url | TEXT | 实时流地址 |
| source_type | VARCHAR | upload / rtsp / file |
| enabled | BOOLEAN | 是否启用 |
| width | INTEGER | 默认宽度 |
| height | INTEGER | 默认高度 |
| fps | FLOAT | 默认帧率 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9.4 frames

用途：存储抽帧信息。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 帧 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| frame_index | INTEGER | 帧序号 |
| timestamp_ms | INTEGER | 时间戳 |
| image_path | TEXT | 帧图像路径 |
| processed | BOOLEAN | 是否处理 |
| created_at | TIMESTAMP | 创建时间 |

### 9.5 detections

用途：存储 YOLOv8 检测结果。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 检测 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| frame_id | FK | 帧 |
| frame_index | INTEGER | 帧序号 |
| class_id | INTEGER | 类别 ID |
| class_name | VARCHAR | 类别 |
| confidence | FLOAT | 置信度 |
| x1 | FLOAT | bbox 左上 x |
| y1 | FLOAT | bbox 左上 y |
| x2 | FLOAT | bbox 右下 x |
| y2 | FLOAT | bbox 右下 y |
| created_at | TIMESTAMP | 创建时间 |

### 9.6 tracks

用途：存储 DeepSORT 跟踪结果。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 记录 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| frame_id | FK | 帧 |
| detection_id | FK | 检测 |
| track_id | INTEGER | 跟踪 ID |
| class_name | VARCHAR | 类别 |
| confidence | FLOAT | 置信度 |
| x1 | FLOAT | bbox 左上 x |
| y1 | FLOAT | bbox 左上 y |
| x2 | FLOAT | bbox 右下 x |
| y2 | FLOAT | bbox 右下 y |
| center_x | FLOAT | 中心点 x |
| center_y | FLOAT | 中心点 y |
| speed | FLOAT | 当前速度 |
| direction_angle | FLOAT | 方向角 |
| state | VARCHAR | tentative / confirmed / lost |
| created_at | TIMESTAMP | 创建时间 |

### 9.7 trajectory_points

用途：存储轨迹点和轨迹特征。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 轨迹点 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| track_id | INTEGER | 跟踪 ID |
| frame_index | INTEGER | 帧序号 |
| timestamp_ms | INTEGER | 时间戳 |
| center_x | FLOAT | 中心点 x |
| center_y | FLOAT | 中心点 y |
| speed | FLOAT | 速度 |
| direction_vector | JSON | 方向向量 |
| moving_angle | FLOAT | 运动角度 |
| dwell_time_ms | INTEGER | 停留时间 |
| zone_history | JSON | 区域历史 |
| lane_relation | JSON | 与车道关系 |
| track_length | INTEGER | 轨迹长度 |
| last_seen | TIMESTAMP | 最近出现 |
| created_at | TIMESTAMP | 创建时间 |

### 9.8 events

用途：存储 Event Engine 识别出的交通事件。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 事件 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| camera_id | FK | 摄像头 |
| track_id | INTEGER | 触发目标 |
| event_type | VARCHAR | 事件类型 |
| severity | VARCHAR | low / medium / high |
| zone_id | FK | 触发区域 |
| start_frame | INTEGER | 起始帧 |
| end_frame | INTEGER | 结束帧 |
| start_time_ms | INTEGER | 起始时间 |
| end_time_ms | INTEGER | 结束时间 |
| confidence | FLOAT | 事件置信度 |
| evidence_json | JSON | 事件证据 |
| snapshot_path | TEXT | 截图 |
| status | VARCHAR | pending / confirmed / false_positive / false_negative / ignored / resolved |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9.9 event_evidence

用途：存储事件证据明细。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 证据 ID |
| event_id | FK | 事件 |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| track_id | INTEGER | 目标 ID |
| frame_index | INTEGER | 证据帧 |
| timestamp_ms | INTEGER | 时间戳 |
| evidence_type | VARCHAR | trajectory / zone / speed / direction / snapshot |
| evidence_json | JSON | 证据内容 |
| snapshot_path | TEXT | 截图路径 |
| created_at | TIMESTAMP | 创建时间 |

### 9.10 alerts

用途：存储告警信息。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 告警 ID |
| event_id | FK | 事件 |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| alert_type | VARCHAR | 告警类型 |
| title | VARCHAR | 标题 |
| message | TEXT | 内容 |
| level | VARCHAR | info / warning / critical |
| status | VARCHAR | new / acknowledged / resolved |
| acknowledged_by | VARCHAR | 确认人 |
| acknowledged_at | TIMESTAMP | 确认时间 |
| resolved_at | TIMESTAMP | 解决时间 |
| created_at | TIMESTAMP | 创建时间 |

### 9.11 event_rules

用途：存储事件规则配置。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 规则 ID |
| name | VARCHAR | 名称 |
| event_type | VARCHAR | 事件类型 |
| enabled | BOOLEAN | 是否启用 |
| zone_id | FK | 绑定区域 |
| target_classes | JSON | 生效类别 |
| parameters_json | JSON | 阈值配置 |
| cooldown_seconds | INTEGER | 冷却时间 |
| severity | VARCHAR | 默认级别 |
| version | INTEGER | 版本 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9.12 zones

用途：存储区域、方向线和计数线配置。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 区域 ID |
| video_id | FK NULL | 视频 |
| camera_id | FK NULL | 摄像头 |
| name | VARCHAR | 区域名称 |
| zone_type | VARCHAR | vehicle_lane / pedestrian_area / no_parking_zone / danger_zone / counting_zone / roi |
| polygon_json | JSON | 多边形点位 |
| direction_json | JSON | 方向线配置 |
| counting_line_json | JSON | 计数线配置 |
| enabled | BOOLEAN | 是否启用 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 9.13 flow_counts

用途：存储车流和人流统计。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 统计 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| zone_id | FK | 区域 |
| counting_line_id | VARCHAR | 计数线 |
| time_window_start_ms | INTEGER | 窗口开始 |
| time_window_end_ms | INTEGER | 窗口结束 |
| class_name | VARCHAR | 类别 |
| in_count | INTEGER | 进入数量 |
| out_count | INTEGER | 离开数量 |
| total_count | INTEGER | 总数 |
| created_at | TIMESTAMP | 创建时间 |

### 9.14 zone_statistics

用途：存储区域统计。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 统计 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| zone_id | FK | 区域 |
| frame_index | INTEGER | 帧序号 |
| timestamp_ms | INTEGER | 时间戳 |
| vehicle_count | INTEGER | 车辆数 |
| person_count | INTEGER | 行人数 |
| avg_speed | FLOAT | 平均速度 |
| occupancy_ratio | FLOAT | 占用率 |
| created_at | TIMESTAMP | 创建时间 |

### 9.15 processing_tasks

用途：存储视频处理任务。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 任务 ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| task_type | VARCHAR | offline_process / realtime_process / evaluation |
| status | VARCHAR | pending / running / completed / failed |
| params_json | JSON | 参数 |
| progress | FLOAT | 进度 |
| error_message | TEXT | 错误 |
| started_at | TIMESTAMP | 开始 |
| finished_at | TIMESTAMP | 结束 |
| created_at | TIMESTAMP | 创建 |

### 9.16 traffic_analysis_runs

用途：记录一次完整视频分析运行。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | run_id |
| video_id | FK | 视频 |
| run_name | VARCHAR | 运行名称 |
| mode | VARCHAR | offline / realtime |
| status | VARCHAR | running / completed / failed |
| detector_config | JSON | 检测参数 |
| tracker_config | JSON | 跟踪参数 |
| event_config | JSON | 事件参数 |
| result_dir | TEXT | 结果目录 |
| artifact_index | JSON | 产物索引 |
| started_at | TIMESTAMP | 开始 |
| finished_at | TIMESTAMP | 结束 |
| created_at | TIMESTAMP | 创建 |

### 9.17 rule_executions

用途：记录事件规则执行结果。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 执行 ID |
| run_id | FK | 分析运行 |
| rule_id | FK | 规则 |
| event_id | FK NULL | 生成事件 |
| track_id | INTEGER | 目标 ID |
| frame_index | INTEGER | 帧 |
| status | VARCHAR | matched / not_matched / skipped / error |
| input_features | JSON | 输入轨迹特征 |
| output_result | JSON | 输出结果 |
| created_at | TIMESTAMP | 创建 |

### 9.18 review_comments

用途：事件复核备注和审计留痕。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 备注 ID |
| event_id | FK NULL | 事件 |
| bad_case_id | FK NULL | Bad Case |
| author | VARCHAR | 复核人 |
| action | VARCHAR | confirm / mark_false_positive / add_false_negative / ignore / resolve |
| before_status | VARCHAR | 修改前 |
| after_status | VARCHAR | 修改后 |
| comment | TEXT | 备注 |
| created_at | TIMESTAMP | 创建 |

### 9.19 bad_cases

用途：存储错误样例。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | Bad Case ID |
| video_id | FK | 视频 |
| run_id | FK | 分析运行 |
| event_id | FK NULL | 事件 |
| frame_id | FK NULL | 帧 |
| track_id | INTEGER | 轨迹 |
| case_type | VARCHAR | false_positive / false_negative / id_switch / track_lost / rule_error / zone_config_error |
| module | VARCHAR | detector / tracker / trajectory / event_engine / zone_config |
| description | TEXT | 描述 |
| expected_result | TEXT | 期望 |
| actual_result | TEXT | 实际 |
| snapshot_path | TEXT | 截图 |
| tags_json | JSON | 标签 |
| status | VARCHAR | open / fixed / verified / ignored |
| created_at | TIMESTAMP | 创建 |
| updated_at | TIMESTAMP | 更新 |

### 9.20 evaluation_datasets

用途：存储评测数据集信息。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 数据集 ID |
| name | VARCHAR | 名称 |
| dataset_type | VARCHAR | detection / tracking / event / flow / regression |
| source | VARCHAR | public_video / public_dataset / custom_annotation |
| annotation_path | TEXT | 标注路径 |
| metadata | JSON | 元数据 |
| created_at | TIMESTAMP | 创建 |

### 9.21 evaluation_results

用途：存储评测结果。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 评测 ID |
| video_id | FK NULL | 视频 |
| run_id | FK NULL | 分析运行 |
| dataset_id | FK NULL | 数据集 |
| evaluation_type | VARCHAR | detection / tracking / trajectory / event / flow_counting / regression |
| metric_name | VARCHAR | 指标名称 |
| metric_value | FLOAT | 指标值 |
| details_json | JSON | 分类别或分事件指标 |
| report_path | TEXT | 报告路径 |
| created_at | TIMESTAMP | 创建 |

### 9.22 model_runs

用途：记录模型和处理参数。

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| id | UUID / BIGINT | 模型运行 ID |
| run_id | FK | 分析运行 |
| model_type | VARCHAR | detector / tracker |
| model_name | VARCHAR | 模型名称 |
| model_version | VARCHAR | 版本 |
| weights_path | TEXT | 权重路径 |
| params_json | JSON | 参数 |
| runtime_ms | INTEGER | 耗时 |
| created_at | TIMESTAMP | 创建 |

### 9.23 表关系

```text
cameras -> videos
videos -> frames
traffic_analysis_runs -> frames / detections / tracks / trajectory_points
detections -> tracks
tracks -> trajectory_points
zones -> event_rules
event_rules -> rule_executions
rule_executions -> events
events -> event_evidence
events -> alerts
events -> review_comments
events -> bad_cases
traffic_analysis_runs -> flow_counts / zone_statistics / evaluation_results
evaluation_datasets -> evaluation_results
model_runs -> traffic_analysis_runs
```

---

## 10. 核心业务流

### 10.1 离线视频分析流

```text
upload video
  -> save file and metadata
  -> create processing_task
  -> create traffic_analysis_run
  -> extract frames
  -> run YOLOv8 detection
  -> run DeepSORT tracking
  -> update trajectory features
  -> run Event Engine
  -> create alerts
  -> write artifacts
  -> index results in Traffic Analysis Center
  -> update task completed
```

### 10.2 实时流分析流

```text
connect stream
  -> read frame
  -> detect
  -> track
  -> update trajectory cache
  -> evaluate events
  -> create alert
  -> retain recent evidence
  -> periodically flush summaries
```

### 10.3 事件复核流

```text
event generated
  -> alert created
  -> reviewer checks video evidence
  -> confirmed / false_positive / ignored / resolved
  -> optional create bad case
  -> optional rerun event rules
```

### 10.4 评测回归流

```text
evaluation dataset
  -> run processing pipeline
  -> calculate metrics
  -> compare expected events / counts
  -> identify failed cases
  -> create bad cases
  -> rerun after fixes
```

---

## 11. 视频管理模块

### 11.1 模块职责

视频管理模块负责视频上传、存储、元数据读取、处理任务创建、处理状态管理、视频预览和分析运行关联。

### 11.2 输入

- 上传视频文件。
- 摄像头或流地址。
- 处理模式：offline / realtime。
- 推理参数：conf_threshold、iou_threshold、frame_stride、max_age、min_hits、event_cooldown。

### 11.3 输出

- videos 记录。
- frames 记录。
- processing_tasks。
- traffic_analysis_runs。
- 视频元数据和处理状态。

### 11.4 核心字段 / Schema

```json
{
  "video_id": "video_001",
  "filename": "road_sample.mp4",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "duration_seconds": 120.5,
  "total_frames": 3615,
  "process_mode": "offline",
  "status": "uploaded"
}
```

### 11.5 业务规则

- 上传后先读取元数据，再允许启动处理。
- 同一视频可多次运行，生成不同 `run_id`。
- 视频处理参数必须绑定到 run_id，保证结果可复现。
- 失败任务需要记录失败阶段和错误原因。

### 11.6 风险点

- 视频编码不兼容。
- 大文件处理时间长。
- 抽帧间隔过大导致事件漏检。
- 多次运行结果混淆。

### 11.7 验收标准

- 支持上传视频并读取 fps、分辨率、时长和总帧数。
- 能创建处理任务并更新状态。
- 能为同一视频创建多次 traffic_analysis_run。
- 前端能查看视频列表和处理状态。

---

## 12. YOLOv8检测模块

### 12.1 模块职责

YOLOv8 检测模块负责对视频帧中的交通参与者进行目标检测，只输出目标类别、bbox 和置信度，不判断交通事件。

### 12.2 输入

- 视频帧图像。
- 模型权重。
- 置信度阈值。
- NMS 阈值。
- 输入尺寸和设备配置。

### 12.3 输出

- detections。
- 标注帧或标注视频中间结果。

### 12.4 推荐检测类别

| 类别 | 说明 |
| --- | --- |
| car | 小汽车 |
| bus | 公交车/大巴 |
| truck | 卡车 |
| motorcycle | 摩托车 |
| bicycle | 自行车 |
| person | 行人 |

### 12.5 检测结果 Schema

```json
{
  "frame_index": 128,
  "timestamp_ms": 4266,
  "detections": [
    {
      "class_name": "car",
      "confidence": 0.91,
      "bbox": [420, 180, 520, 260]
    }
  ]
}
```

### 12.6 业务规则

- 检测模块封装为 `YoloDetector`，API 层不直接调用模型。
- 模型路径、阈值、输入尺寸、设备和类别映射可配置。
- 检测结果必须写入 detections。
- 检测评测不能只看单张可视化，应结合 mAP、Precision、Recall 和 Bad Case。

### 12.7 风险点

- 小目标、夜间、遮挡、反光和运动模糊导致漏检。
- 误检目标进入跟踪和事件链路。
- 置信度阈值过高导致 Recall 下降，过低导致误报增加。

### 12.8 验收标准

- 能对视频帧输出 bbox、class_name 和 confidence。
- detections 表字段稳定。
- 能配置模型路径和阈值。
- 检测结果可被 DeepSORT 读取。

---

## 13. DeepSORT多目标跟踪模块

### 13.1 模块职责

DeepSORT 多目标跟踪模块负责把每帧独立检测结果关联成连续轨迹，为每个目标分配稳定 `track_id`，为轨迹分析和事件判断提供时间维度。

### 13.2 输入

- 当前帧检测框。
- 类别和置信度。
- 当前帧图像。
- 跟踪参数：max_age、min_hits、iou_threshold、embedding 配置。

### 13.3 输出

- tracks。
- track_id、bbox、center、state。

### 13.4 跟踪输出 Schema

```json
{
  "frame_index": 128,
  "tracks": [
    {
      "track_id": 17,
      "class_name": "car",
      "bbox": [420, 180, 520, 260],
      "center": [470, 220],
      "confidence": 0.88,
      "state": "confirmed"
    }
  ]
}
```

### 13.5 业务规则

- 只有 confirmed track 才进入稳定事件判断。
- 短轨迹不应触发逆行和违停等事件。
- track lost 应保留 last_seen，用于判断轨迹中断。
- ID Switch 和 Track Lost 需要进入 Bad Case。

### 13.6 风险点

- 遮挡导致 ID Switch。
- 检测漏检导致轨迹中断。
- 密集交通导致目标关联错误。
- 远距离小目标形成短轨迹。

### 13.7 验收标准

- 能为同一目标维护稳定 track_id。
- tracks 写入 frame_index、track_id、bbox、center 和 state。
- 前端能展示 track_id 和轨迹线。
- 跟踪评测支持 IDF1、MOTA 和 ID Switch。

---

## 14. Trajectory Engine轨迹分析模块

### 14.1 模块职责

Trajectory Engine 负责把 DeepSORT 输出的连续 track 点转换为可用于事件判断的轨迹特征，包括中心点序列、速度、方向、停留时间、区域历史、车道关系、轨迹长度和最近出现时间。

### 14.2 输入

- tracks。
- zones。
- direction line。
- counting line。
- 帧率和时间戳。

### 14.3 输出

- trajectory_points。
- track feature cache。
- zone_statistics。
- flow_count candidates。

### 14.4 核心轨迹特征

| 特征 | 说明 |
| --- | --- |
| center_points | 目标中心点序列 |
| speed | 单位时间内像素位移或估算速度 |
| direction_vector | 运动方向向量 |
| moving_angle | 运动角度 |
| dwell_time | 在某区域内停留时间 |
| zone_history | 目标进入过的区域列表 |
| lane_relation | 目标与机动车道/禁行区关系 |
| track_length | 轨迹持续帧数 |
| last_seen | 最近出现时间 |

### 14.5 轨迹缓存 Schema

```json
{
  "track_id": 17,
  "class_name": "car",
  "center_points": [
    {
      "frame_index": 120,
      "x": 450,
      "y": 230,
      "timestamp_ms": 4000
    }
  ],
  "speed": 6.1,
  "direction_vector": [1.0, 0.1],
  "moving_angle": 7.5,
  "dwell_time_ms": 0,
  "zone_history": ["lane_1"],
  "lane_relation": {
    "current_zone": "vehicle_lane"
  },
  "track_length": 24,
  "last_seen": "2026-01-01T00:00:00Z"
}
```

### 14.6 几何计算能力

- 点是否在多边形区域内。
- bbox bottom-center 是否在指定区域。
- 轨迹线是否穿越方向线或计数线。
- 当前运动方向与道路允许方向夹角。
- 目标在区域内持续时间。
- 区域内目标数量和平均速度。

### 14.7 风险点

- 轨迹太短导致方向不稳定。
- 像素速度不能直接等同真实速度。
- 透视变化导致远近区域速度差异。
- 区域边界点抖动造成频繁进出。

### 14.8 验收标准

- 能保存 trajectory_points。
- 能计算速度、moving_angle、dwell_time、zone_history。
- 能判断点在多边形内和轨迹穿线。
- 能为 Event Engine 提供稳定输入。

---

## 15. Event Engine事件规则模块

### 15.1 模块职责

Event Engine 负责读取轨迹特征、区域配置、方向配置和事件规则，生成交通事件、事件证据和规则执行记录。Event Engine 不做模型推理。

### 15.2 输入

- track 当前状态。
- track 历史轨迹。
- zones。
- direction lines。
- event_rules。
- flow counting state。

### 15.3 输出

- events。
- event_evidence。
- alerts。
- rule_executions。

### 15.4 事件输出 Schema

```json
{
  "event_type": "wrong_way_driving",
  "severity": "high",
  "track_id": 17,
  "zone_id": "main_lane",
  "start_frame": 340,
  "end_frame": 358,
  "confidence": 0.86,
  "evidence": {
    "direction_angle": 184.2,
    "allowed_angle": 0,
    "angle_diff": 175.8,
    "speed": 8.4,
    "frame_index": 358,
    "snapshot_path": "keyframes/event_23.jpg"
  }
}
```

### 15.5 业务规则

- 检测、跟踪、轨迹和事件判断必须解耦。
- 事件规则应配置化，不硬编码在推理流程中。
- 每个事件必须保存证据。
- 同一 track 和同一规则需要去重。
- 事件判断支持 `cooldown_seconds`。
- 高风险事件自动生成 alert。

### 15.6 风险点

- 区域配置不准确导致误报。
- 阈值过严导致漏报，过松导致误报。
- 目标抖动导致事件重复触发。
- track_id 切换导致事件断裂。

### 15.7 验收标准

- 支持规则配置和启用/禁用。
- 支持事件去重和冷却时间。
- 每个事件有 event_evidence。
- rule_executions 可查询。
- 能生成 alerts。

---

## 16. 事件类型设计

### 16.1 车辆逆行检测

目标：识别车辆运动方向与配置道路允许方向明显相反的情况。

适用类别：

- car。
- bus。
- truck。
- motorcycle。

规则条件：

- 目标位于 vehicle_lane。
- track_length 大于最小帧数。
- moving_angle 与 allowed_angle 夹角大于 reverse_angle_threshold。
- speed 大于 min_speed，避免静止抖动误判。
- 连续满足条件超过 confirm_frames。

关键参数：

| 参数 | 示例 |
| --- | --- |
| min_track_frames | 10 |
| reverse_angle_threshold | 135 |
| min_speed | 3 px/frame |
| confirm_frames | 5 |
| cooldown_seconds | 10 |

### 16.2 违停检测

目标：识别车辆在 no_parking_zone 或道路区域内长时间静止。

规则条件：

- 目标类别为车辆。
- 目标位于 no_parking_zone 或 vehicle_lane。
- speed 低于 stop_speed_threshold。
- dwell_time 超过 min_dwell_seconds。
- 中心点偏移小于 max_center_shift。

### 16.3 危险区域闯入

目标：识别车辆或行人进入 danger_zone。

规则条件：

- 目标中心点或 bbox bottom-center 进入 danger_zone。
- 持续时间超过 min_inside_frames。
- 区域规则启用。

### 16.4 行人进入机动车道

目标：识别 person 进入 vehicle_lane。

规则条件：

- class_name 为 person。
- bottom-center 位于 vehicle_lane polygon 内。
- 持续时间超过 min_inside_seconds。

### 16.5 拥堵检测

目标：识别区域内车辆数量较多且平均速度较低的拥堵状态。

规则条件：

- 指定区域内车辆数量超过 vehicle_count_threshold。
- 区域内车辆平均速度低于 avg_speed_threshold。
- 状态持续超过 time_window_seconds。

### 16.6 车流 / 人流统计

目标：统计单位时间内穿越 counting line 的车辆数和行人数。

规则条件：

- track 轨迹穿越计数线。
- 同一 track_id 对同一计数线只计数一次或按冷却时间计数。
- 按方向区分 in_count 和 out_count。

统计输出：

| 指标 | 说明 |
| --- | --- |
| vehicle_count | 车辆通过数量 |
| person_count | 行人通过数量 |
| in_count | 进入方向数量 |
| out_count | 离开方向数量 |
| count_per_minute | 每分钟流量 |

---

## 17. 区域划线与方向配置模块

### 17.1 模块职责

区域划线与方向配置模块负责把视频画面中的道路、行人区域、禁停区域、危险区域、统计区域和 ROI 转化为可被规则引擎读取的几何配置。

### 17.2 区域类型

| 区域类型 | 说明 |
| --- | --- |
| vehicle_lane | 机动车道 |
| pedestrian_area | 行人区域 |
| no_parking_zone | 禁停区域 |
| danger_zone | 危险区域 |
| counting_zone | 统计区域 |
| roi | 推理关注区域 |

### 17.3 区域 Schema

```json
{
  "zone_id": "zone_001",
  "name": "main_lane",
  "zone_type": "vehicle_lane",
  "polygon": [
    [120, 220],
    [900, 210],
    [1050, 620],
    [80, 640]
  ],
  "enabled": true
}
```

### 17.4 方向配置

```json
{
  "direction_id": "lane_1_direction",
  "zone_id": "zone_001",
  "start_point": [180, 500],
  "end_point": [850, 500],
  "allowed_angle": 0,
  "reverse_angle_threshold": 135
}
```

### 17.5 计数线配置

```json
{
  "counting_line_id": "line_001",
  "zone_id": "zone_001",
  "start_point": [300, 100],
  "end_point": [300, 700],
  "in_direction": "left_to_right",
  "enabled": true
}
```

### 17.6 业务规则

- 区域配置按 video_id 或 camera_id 保存。
- 区域和方向线修改后不应覆盖历史 run 的配置，应通过 run 配置快照保证可复现。
- 区域边界附近事件应保留坐标证据。
- counting line 与 direction line 需区分用途。

### 17.7 风险点

- 区域绘制不准确导致误报。
- 视频分辨率变化导致坐标映射错误。
- 道路透视导致 allowed_angle 难以统一。
- 计数线方向配置错误导致进出方向反转。

### 17.8 验收标准

- 前端可绘制 polygon、direction line 和 counting line。
- 配置可保存、读取和回显。
- Event Engine 能读取配置。
- 区域配置错误可进入 Bad Case。

---

## 18. Traffic Analysis Center结果分析中心

### 18.1 模块职责

Traffic Analysis Center 负责统一管理一次视频分析产生的全部结果。它不做模型推理，也不做事件判断；它是结果管理层，按 `video_id` / `run_id` 组织检测、跟踪、轨迹、事件、告警、统计、关键帧、标注视频、评测产物和 Bad Case 链接，让 Dashboard、Review Center、Evaluation Center 和 API 从统一结果索引读取数据。

### 18.2 输入

- video metadata。
- detections。
- tracks。
- trajectory_points。
- events。
- alerts。
- flow_counts。
- zone_statistics。
- annotated_video。
- keyframes。
- evaluation artifacts。
- Bad Case links。

### 18.3 输出

- traffic_analysis_runs。
- metadata.json。
- artifact_index。
- 结果查询 API。
- 导出文件。

### 18.4 推荐结果目录

```text
results/traffic_analysis/<run_id>/
  metadata.json
  detections.csv
  tracks.csv
  trajectory_points.csv
  events.jsonl
  alerts.jsonl
  flow_counts.json
  zone_statistics.json
  bad_cases.csv
  evaluation_summary.json
  annotated_video.mp4
  keyframes/
```

### 18.5 metadata.json

```json
{
  "run_id": "run_001",
  "video_id": "video_001",
  "input_video": "local_videos/road.mp4",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "detector_config": {},
  "tracker_config": {},
  "event_config": {},
  "started_at": "",
  "finished_at": "",
  "artifacts": {
    "detections": "detections.csv",
    "tracks": "tracks.csv",
    "events": "events.jsonl",
    "annotated_video": "annotated_video.mp4"
  }
}
```

### 18.6 业务规则

- 每次视频分析必须生成唯一 run_id。
- run_id 绑定检测、跟踪、事件、评测和结果文件。
- Dashboard、Review Center 和 Evaluation Center 不直接扫文件目录，应通过 Traffic Analysis Center 查询索引。
- 结果产物可重新导出，但历史 run 的参数和结果不能被静默覆盖。

### 18.7 风险点

- 多次运行结果混淆。
- 文件产物和数据库索引不一致。
- 标注视频体积过大。
- keyframes 和事件证据路径失效。

### 18.8 验收标准

- 能按 run_id 查询全部结果。
- 能生成推荐目录中的核心产物。
- 能为 Dashboard、Review Center 和 Evaluation Center 提供统一数据源。
- 能导出结果摘要和明细。

---

## 19. Alert Center告警中心

### 19.1 模块职责

Alert Center 负责将 Event Engine 生成的事件转化为告警，管理告警状态，并为 Dashboard 提供待处理事件视图。

### 19.2 输入

- events。
- event_evidence。
- event_rules severity。
- Review Center 状态变更。

### 19.3 输出

- alerts。
- 告警列表。
- 告警统计。

### 19.4 告警状态

```text
new
acknowledged
resolved
ignored
```

### 19.5 业务规则

- 高严重度事件自动生成告警。
- 同一 track、同一区域、同一事件类型在冷却时间内不重复告警。
- 告警关闭不等于事件正确，事件正确性由 Review Center 维护。
- 告警应关联事件证据和关键帧。

### 19.6 验收标准

- 能从事件生成告警。
- 能确认和关闭告警。
- Dashboard 能展示未处理告警数量和最近告警。
- 告警能跳转到事件详情。

---

## 20. Review Center事件复核模块

### 20.1 模块职责

Review Center 负责事件复核、误报标记、漏报补充、状态修改、复核备注、Bad Case 关联、规则重跑和审计留痕。

### 20.2 触发复核的情况

- Event Engine 生成高严重度事件。
- 事件置信度低。
- 事件证据不完整。
- 用户认为事件误报。
- 用户发现系统漏报。
- 区域或方向线配置可能错误。
- Evaluation Center 发现失败样例。
- Bad Case 回归失败。

### 20.3 复核状态

```text
pending
confirmed
false_positive
false_negative
ignored
resolved
```

### 20.4 复核动作

| 动作 | 说明 |
| --- | --- |
| 人工确认事件 | 将事件状态改为 confirmed |
| 标记误报 | 将事件状态改为 false_positive |
| 标记漏报 | 创建 false_negative 记录或补充事件 |
| 修改事件状态 | pending / ignored / resolved 等状态流转 |
| 补充复核备注 | 写入 review_comments |
| 关联 Bad Case | 将事件关联到 bad_cases |
| 重新运行事件规则 | 使用修正后的区域或阈值重跑 |
| 审计留痕 | 记录 before_status、after_status、comment 和时间 |

### 20.5 输入

- events。
- event_evidence。
- alerts。
- keyframes。
- 用户复核动作。

### 20.6 输出

- review_comments。
- 更新后的 events.status。
- Bad Case 记录。
- 规则重跑任务。

### 20.7 业务规则

- 状态变更必须写 review_comments。
- false_positive 应记录错误来源。
- false_negative 应记录期望事件类型、帧范围和证据。
- 重新运行规则应生成新的 run 或规则执行记录，不覆盖旧结果。

### 20.8 验收标准

- 能筛选 pending 事件。
- 能确认事件、标记误报、补充漏报。
- 能写复核备注。
- 能关联 Bad Case。
- 能触发事件规则重跑。

---

## 21. Bad Case体系

### 21.1 模块职责

Bad Case 体系用于记录检测、跟踪、轨迹、规则、区域配置和复核过程中的错误，并将错误转化为可复查、可归因、可修复、可回归的工程资产。

### 21.2 Bad Case 类型

| 类型 | 说明 |
| --- | --- |
| false_positive | 系统报了事件，但实际没有事件 |
| false_negative | 实际有事件，但系统未检测出来 |
| id_switch | 同一目标跟踪 ID 发生切换 |
| track_lost | 目标被遮挡或远离后轨迹丢失 |
| rule_error | 检测和跟踪正确，但事件规则判断错误 |
| zone_config_error | 区域或方向线配置导致误判 |

### 21.3 Bad Case 标签

| 标签 | 说明 |
| --- | --- |
| night | 夜间 |
| occlusion | 遮挡 |
| small_object | 远距离小目标 |
| motion_blur | 运动模糊 |
| crowded | 密集交通 |
| reflection | 反光 |
| wrong_zone | 区域配置不准 |
| wrong_direction | 方向线配置不准 |

### 21.4 Bad Case Schema

```json
{
  "case_id": "bc_001",
  "case_type": "false_positive",
  "module": "event_engine",
  "video_id": "video_001",
  "run_id": "run_001",
  "event_id": "event_001",
  "track_id": 17,
  "expected_result": "no event",
  "actual_result": "wrong_way_driving",
  "root_cause": "direction line angle configured incorrectly",
  "tags": ["wrong_direction"],
  "snapshot_path": "keyframes/event_001.jpg",
  "status": "open"
}
```

### 21.5 处理流程

```text
review event
  -> mark error type
  -> select source module
  -> attach snapshot and evidence
  -> write expected and actual result
  -> add tags
  -> adjust model / tracker / trajectory / rule / zone config
  -> rerun evaluation
  -> update case status
```

### 21.6 验收标准

- 能创建、筛选和更新 Bad Case。
- Bad Case 能关联 event、track、frame 和 run。
- 能按类型、模块和标签统计。
- 能加入回归评测。

---

## 22. Evaluation Center评测体系

### 22.1 模块职责

Evaluation Center 负责管理评测数据集、执行检测评测、跟踪评测、轨迹评测、事件评测、流量统计评测和 Bad Case 回归评测，并展示指标、失败样例和评测产物。

### 22.2 检测评测

| 指标 | 说明 |
| --- | --- |
| mAP | 检测框和类别预测整体效果 |
| Precision | 预测为目标的结果中正确比例 |
| Recall | 真实目标中被检测出来的比例 |
| per-class AP | 分类别 AP |

### 22.3 跟踪评测

| 指标 | 说明 |
| --- | --- |
| IDF1 | 目标身份保持能力 |
| MOTA | 综合考虑误检、漏检和 ID Switch |
| ID Switch | 目标 ID 切换次数 |

### 22.4 轨迹评测

| 指标 | 说明 |
| --- | --- |
| track length | 平均轨迹长度 |
| lost track | 轨迹丢失数量 |
| speed consistency | 速度变化是否稳定 |
| direction consistency | 方向估计是否稳定 |

### 22.5 事件评测

| 指标 | 说明 |
| --- | --- |
| Event Accuracy | 事件判断准确率 |
| False Alarm Rate | 误报率 |
| Event Recall | 真实事件召回率 |
| Event F1 | 事件综合指标 |
| per-event metrics | 分事件类型指标 |

### 22.6 流量统计评测

| 指标 | 说明 |
| --- | --- |
| MAE | 平均绝对误差 |
| MAPE | 平均绝对百分比误差 |
| direction-wise error | 按方向误差 |
| class-wise error | 按类别误差 |

### 22.7 Bad Case 回归评测

| 指标 | 说明 |
| --- | --- |
| regression pass rate | 回归通过率 |
| reopened case count | 修复后复发数量 |
| fixed case count | 已修复数量 |

### 22.8 评测产物

```text
evals/results/<run_name>/
  metrics.json
  failed_cases.json
  detection_report.csv
  tracking_report.csv
  event_report.csv
  flow_counting_report.csv
  regression_report.csv
```

### 22.9 验收标准

- 能记录 evaluation_datasets。
- 能保存 evaluation_results。
- 能按 run_id 查询评测产物。
- 能把失败样例转为 Bad Case。
- 能展示检测、跟踪、轨迹、事件、流量和回归指标。

---

## 23. 离线与实时处理模式

### 23.1 离线模式

适用场景：

- 上传视频文件。
- 完整视频分析。
- 结果复查。
- 评测和 Bad Case 分析。

特点：

- 可重复运行。
- 完整保存检测、跟踪、轨迹、事件和告警。
- 便于生成标注视频、关键帧、统计和评测报告。

### 23.2 实时模式

适用场景：

- RTSP 视频流。
- 本地摄像头。
- 模拟实时监控。

特点：

- 持续处理。
- 更关注延迟和吞吐。
- 只保留近期帧、关键帧和事件证据。
- 评测难度高于离线模式。

### 23.3 差异对比

| 维度 | 离线模式 | 实时模式 |
| --- | --- | --- |
| 输入 | 上传视频文件 | 摄像头流 / RTSP |
| 处理目标 | 完整分析和复盘 | 持续监控和告警 |
| 输出 | 完整结果、标注视频、评测报告 | 实时事件、告警流、近期缓存 |
| 评测 | 更适合 | 较复杂 |
| Bad Case | 更容易沉淀 | 需要截图和缓存策略 |

### 23.4 验收标准

- 离线模式能完整保存 run 结果。
- 实时模式可作为可选能力。
- 两种模式使用同一套检测、跟踪、轨迹和事件模块。
- 实时模式不影响离线评测闭环。

---

## 24. 开发阶段规划

### 阶段一：项目骨架与视频管理

目标：

- 搭建 FastAPI 后端、React 前端和基础数据库。
- 完成视频上传、元数据读取、视频列表和处理任务状态。

开发任务：

- 创建 backend、frontend、docs、evals、results 目录。
- 实现 videos、frames、processing_tasks、traffic_analysis_runs 表。
- 实现视频上传和元数据读取。
- 实现 Dashboard 和 Video Center 初版。

交付物：

- 项目骨架。
- 视频上传 API。
- 视频列表页面。
- 处理任务状态。

验收标准：

- 上传视频后可看到 videos 记录。
- 前端能查看视频元数据和状态。
- 同一视频可创建 run_id。

### 阶段二：YOLOv8 检测接入

目标：

- 封装 YOLOv8 检测服务并写入 detections。

开发任务：

- 实现 `YoloDetector`。
- 配置模型路径、阈值、输入尺寸和设备。
- 对视频帧执行检测。
- 保存 detections。
- 生成检测预览。

交付物：

- 检测服务。
- detections 表数据。
- 检测预览产物。

验收标准：

- 可检测车辆和行人。
- detections 字段稳定。
- 检测参数可配置。

### 阶段三：DeepSORT 多目标跟踪

目标：

- 接入 DeepSORT，生成稳定 track_id。

开发任务：

- 实现 `DeepSortTracker`。
- 读取 detections 并生成 tracks。
- 保存 track_id、bbox、center 和 state。
- 前端叠加 track_id 和轨迹线。

交付物：

- 跟踪服务。
- tracks 数据。
- 轨迹展示。

验收标准：

- 同一目标在多帧中保持稳定 ID。
- 能记录 ID Switch 和 Track Lost 样例。

### 阶段四：Trajectory Engine 轨迹分析

目标：

- 计算速度、方向、停留时间、区域关系和穿线行为。

开发任务：

- 实现 trajectory cache。
- 实现 geometry 工具。
- 保存 trajectory_points。
- 实现 zone_history、lane_relation 和 dwell_time。

交付物：

- Trajectory Engine。
- trajectory_points 数据。
- 几何工具测试。

验收标准：

- 能查询单个 track 的轨迹、速度和方向。
- 能判断进入区域和穿越计数线。

### 阶段五：Event Engine 与事件规则

目标：

- 实现主要事件规则并生成 events、event_evidence 和 alerts。

开发任务：

- 实现逆行、违停、危险区域闯入、行人进入机动车道、拥堵和流量统计。
- 实现事件去重和冷却时间。
- 实现 rule_executions。
- 实现 Alert Center 基础 API。

交付物：

- Event Engine。
- events、event_evidence、alerts。
- 事件规则配置。

验收标准：

- 至少三类事件可在样例视频中触发。
- 每个事件都有 evidence。
- 告警可查询。

### 阶段六：Traffic Analysis Center 与结果管理

目标：

- 按 run_id 管理一次视频分析的全部产物。

开发任务：

- 实现 traffic_analysis_runs。
- 实现结果目录写入。
- 生成 metadata.json、detections.csv、tracks.csv、trajectory_points.csv、events.jsonl、alerts.jsonl。
- 生成关键帧和标注视频。

交付物：

- Traffic Analysis Center。
- 结果目录。
- 统一结果查询 API。

验收标准：

- Dashboard 和 API 能按 run_id 读取全部结果。
- 结果产物和数据库索引一致。

### 阶段七：Dashboard、Alert Center 与 Review Center

目标：

- 完成可视化、告警处理和事件复核闭环。

开发任务：

- 实现视频叠加层。
- 实现事件列表、事件时间轴和告警面板。
- 实现 Review Center。
- 支持确认事件、标记误报、补充漏报、备注和关联 Bad Case。

交付物：

- Dashboard。
- Alert Center。
- Review Center。

验收标准：

- 可播放标注视频并查看事件。
- 可处理告警。
- 可复核事件并生成 review_comments。

### 阶段八：Bad Case 与 Evaluation Center

目标：

- 建立错误样例和评测回归体系。

开发任务：

- 实现 Bad Case Center。
- 建立 evaluation_datasets。
- 实现检测、跟踪、轨迹、事件、流量和回归评测。
- 支持失败样例转 Bad Case。

交付物：

- Bad Case Center。
- Evaluation Center。
- 评测报告。

验收标准：

- 可查看 mAP、Precision、Recall、IDF1、MOTA、Event Accuracy、False Alarm Rate、Event Recall、Event F1、MAE、MAPE。
- Bad Case 可进入回归评测。

### 阶段九：工程化、Docker、README 与演示数据

目标：

- 完成可复现、可交付、可验收的工程形态。

开发任务：

- 补齐 Docker Compose、`.env.example`、`.gitignore`。
- 整理 README、API 文档、数据库文档、事件规则文档、评测文档。
- 准备公开视频、公开数据集或模拟区域配置样例。
- 编写数据与安全说明。

交付物：

- Docker Compose。
- README。
- docs 文档集。
- 样例视频和配置说明。

验收标准：

- 新环境能按 README 启动。
- 不提交模型权重、大视频和批量结果。
- 文档覆盖检测、跟踪、轨迹、事件、结果管理、复核和评测。

---

## 25. README模板

```markdown
# SmartTraffic 智慧交通事件检测系统

SmartTraffic 是基于 YOLOv8、DeepSORT、Trajectory Engine、Event Engine、Traffic Analysis Center、Review Center、Evaluation Center、FastAPI、React 和数据库的智慧交通事件检测平台，支持交通视频离线分析、可选实时流处理、目标检测、多目标跟踪、轨迹事件判断、区域划线、告警、复核、结果导出和评测闭环。

## 项目简介

系统围绕“视频输入 -> YOLOv8 目标检测 -> DeepSORT 多目标跟踪 -> Trajectory Engine 轨迹分析 -> Event Engine 事件规则判断 -> Alert Center 告警 -> Dashboard 展示与复核 -> Evaluation Center + Bad Case 闭环”构建。

## 项目边界

- 不作为正式交通执法依据。
- 不宣称生产部署或商业效果。
- 事件结果需要人工复核。
- 指标只填写真实评测结果。
- 模型结果必须可追溯到视频帧、轨迹和规则证据。

## 技术栈

- Backend: FastAPI, Pydantic, SQLAlchemy
- CV: YOLOv8, PyTorch, OpenCV
- Tracking: DeepSORT
- Frontend: React, TypeScript, Vite
- Visualization: HTML5 Video, Canvas/SVG Overlay, ECharts/Recharts
- Database: PostgreSQL or SQLite prototype
- Deployment: Docker Compose

## 核心功能

- 视频管理
- 视频上传
- 离线视频处理
- 可选实时流处理
- YOLOv8 目标检测
- DeepSORT 多目标跟踪
- Trajectory Engine 轨迹分析
- Event Engine 事件规则判断
- 区域划线与方向配置
- Traffic Analysis Center
- Alert Center
- Review Center
- Bad Case Center
- Evaluation Center
- Dashboard
- 报告与结果导出

## 系统架构

说明 Frontend、FastAPI、Processing Services、Traffic Analysis Center、Database、File Storage 和 Evaluation Datasets。

## 本地运行

```bash
docker compose up --build
```

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 数据与安全说明

- 使用公开视频、公开数据集、模拟区域配置和自建少量标注样例。
- 不提交模型权重、大视频、批量处理结果和本地缓存。
- 原视频、标注视频、关键帧和评测产物默认进入本地结果目录。

## API说明

- Video APIs
- Processing APIs
- Detection / Tracking / Trajectory APIs
- Event APIs
- Alert APIs
- Zone / Rule APIs
- Traffic Analysis APIs
- Review APIs
- Bad Case APIs
- Evaluation APIs

## YOLOv8检测说明

YOLOv8 负责目标检测，输出 bbox、class_name、confidence、frame_index 和 timestamp，不负责交通事件判断。

## DeepSORT跟踪说明

DeepSORT 将单帧检测结果关联成连续轨迹，为目标分配 track_id，为逆行、违停、拥堵和流量统计提供时间维度。

## Trajectory Engine说明

Trajectory Engine 计算 center_points、speed、direction_vector、moving_angle、dwell_time、zone_history、lane_relation、track_length 和 last_seen。

## Event Engine说明

Event Engine 根据轨迹特征、区域、方向线、计数线和规则阈值判断车辆逆行、违停、危险区域闯入、行人进入机动车道、拥堵和流量统计事件。

## Traffic Analysis Center说明

Traffic Analysis Center 按 run_id 统一管理 detections、tracks、trajectory_points、events、alerts、flow_counts、zone_statistics、keyframes、annotated_video、evaluation artifacts 和 Bad Case links。

## Review Center说明

Review Center 支持事件确认、误报标记、漏报补充、状态修改、复核备注、Bad Case 关联和规则重跑。

## Evaluation Center说明

Evaluation Center 覆盖检测、跟踪、轨迹、事件、流量统计和 Bad Case 回归评测。

## 后续规划

- 增强实时流处理。
- 扩展更多事件规则。
- 增强轨迹质量评估。
- 完善 Evaluation Center 指标看板。
- 增加更多公开视频评测样例。
```

---

## 26. 最终验收标准

### 26.1 功能验收

- 可上传视频并读取元数据。
- 可创建离线处理任务。
- 可执行 YOLOv8 检测。
- 可执行 DeepSORT 跟踪。
- 可生成 trajectory_points。
- 可执行 Event Engine 事件判断。
- 可生成 alerts。
- 可配置区域、方向线和计数线。
- 可在 Dashboard 查看视频、检测框、轨迹、事件和告警。
- 可在 Review Center 复核事件。
- 可在 Traffic Analysis Center 查询 run 结果。

### 26.2 工程验收

- FastAPI 后端可启动。
- React 前端可启动。
- 数据库迁移可运行。
- API 响应 Schema 稳定。
- 检测、跟踪、轨迹、事件模块分层清晰。
- 长任务有 processing_tasks 状态。
- 配置和结果按 run_id 绑定。
- 单元测试覆盖几何计算、事件规则、流量统计和复核流程。

### 26.3 数据库验收

- videos、cameras、frames、detections、tracks 可支撑视频和检测跟踪。
- trajectory_points 可支撑轨迹分析。
- events、event_evidence、alerts、event_rules、zones 可支撑事件和告警。
- flow_counts、zone_statistics 可支撑统计。
- processing_tasks、traffic_analysis_runs 可支撑任务和结果管理。
- rule_executions、review_comments 可支撑规则追踪和复核。
- bad_cases、evaluation_datasets、evaluation_results 可支撑质量闭环。
- model_runs 可支撑模型运行记录。

### 26.4 YOLOv8检测验收

- 支持车辆和行人相关类别检测。
- 检测结果写入 detections。
- 支持阈值和模型路径配置。
- 评测支持 mAP、Precision、Recall。

### 26.5 DeepSORT跟踪验收

- 能生成稳定 track_id。
- tracks 保存 bbox、center、state、frame_index。
- 支持 IDF1、MOTA、ID Switch 评测。
- ID Switch 和 Track Lost 可进入 Bad Case。

### 26.6 Trajectory Engine验收

- 能计算 center_points、speed、direction_vector、moving_angle、dwell_time、zone_history、lane_relation、track_length、last_seen。
- 能判断点在区域内和轨迹穿线。
- 能支撑事件规则输入。

### 26.7 Event Engine验收

- 支持车辆逆行、违停、危险区域闯入、行人进入机动车道、拥堵和流量统计。
- 事件规则可配置。
- 支持冷却时间和去重。
- 每个事件有 event_evidence。

### 26.8 Traffic Analysis Center验收

- 每次分析有唯一 run_id。
- 能生成 metadata.json、detections.csv、tracks.csv、trajectory_points.csv、events.jsonl、alerts.jsonl、flow_counts.json、zone_statistics.json、evaluation_summary.json、annotated_video.mp4 和 keyframes。
- Dashboard、Review Center 和 Evaluation Center 从统一结果索引读取数据。

### 26.9 Alert Center验收

- 高严重度事件可生成告警。
- 告警支持 new、acknowledged、resolved、ignored 状态。
- 告警能跳转事件证据。

### 26.10 Review Center验收

- 支持 pending、confirmed、false_positive、false_negative、ignored、resolved 状态。
- 支持人工确认事件、标记误报、补充漏报、修改状态和备注。
- 支持关联 Bad Case。
- 支持重新运行事件规则。

### 26.11 Bad Case验收

- 支持 false_positive、false_negative、id_switch、track_lost、rule_error、zone_config_error。
- Bad Case 可关联 video、run、event、frame、track。
- 支持标签和根因。
- 支持回归评测。

### 26.12 Evaluation Center验收

- 支持检测评测：mAP、Precision、Recall。
- 支持跟踪评测：IDF1、MOTA、ID Switch。
- 支持轨迹评测：track length、lost track、speed/direction consistency。
- 支持事件评测：Event Accuracy、False Alarm Rate、Event Recall、Event F1。
- 支持流量统计评测：MAE、MAPE。
- 支持 Bad Case Regression：regression pass rate。

### 26.13 安全与数据验收

- 不提交模型权重。
- 不提交大视频和批量处理结果。
- 不提交本地缓存和临时文件。
- 样例数据使用公开视频、公开数据集、模拟区域配置或自建少量标注样例。
- 结果说明中标注不构成正式交通执法依据。

### 26.14 文档验收

- README 包含项目简介、项目边界、技术栈、核心功能、系统架构、本地运行、数据与安全说明、API、YOLOv8、DeepSORT、Trajectory Engine、Event Engine、Traffic Analysis Center、Review Center、Evaluation Center 和后续规划。
- docs 包含架构、API、数据库、事件规则、区域配置和评测说明。
- 主开发手册保持项目化、工程化、可执行、可验收。
- 展示性材料与主开发规格分离。

---

本手册作为 SmartTraffic 智慧交通事件检测系统最终版项目开发执行规格，后续开发应围绕“检测可评估、跟踪可追踪、轨迹可解释、事件可复核、结果可管理、告警可处理、错误可回归”的目标展开。
