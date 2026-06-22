# SmartTraffic 智慧交通事件检测系统

SmartTraffic 是面向交通视频离线分析的智慧交通事件检测系统。当前仓库已完成阶段二：YOLOv8 检测接入，支持视频上传、视频元数据读取、YOLOv8 dry-run 检测、可选真实 YOLOv8 推理、检测结果产物写入和基础前端查看。

## 项目边界

- 当前不实现完整 DeepSORT、Trajectory Engine、Event Engine、Alert Center、Review Center、Bad Case Center 或 Evaluation Center。
- YOLOv8 检测适配器只负责模型加载和检测结果格式化，不判断交通事件。
- 事件结果不作为正式交通执法依据。
- 模型权重、大视频、本地输出结果和缓存文件不提交到 Git。

## 技术栈

- Backend: FastAPI, Pydantic, OpenCV, pytest
- CV: YOLOv8 adapter contract, dry-run by default
- Frontend: React, TypeScript, Vite
- Storage: local files for stage-two detection artifacts

## 当前阶段能力

- 视频上传到本地 `local_videos/`
- 使用 OpenCV 读取 `fps`、`width`、`height`、`total_frames`、`duration_seconds`
- `YoloDetector` 支持 dry-run 与可选真实 YOLOv8 推理
- `DetectionService` 可按 `frame_stride`、`max_frames` 处理视频帧
- 每次处理生成独立 `run_id`
- 写入 `detections.csv`、`detections.jsonl`、`detection_summary.json`
- 前端可上传视频、启动 dry-run 检测、查看 run 摘要和帧级检测列表

## 尚未开始

- DeepSORT 多目标跟踪
- Trajectory Engine
- Event Engine
- Alert / Review / Bad Case / Evaluation 完整逻辑
- 正式实时流处理

## 本地运行

后端：

```bash
cd /Users/jiaxulong/Documents/smarttraffic/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd /Users/jiaxulong/Documents/smarttraffic/frontend
npm install
npm run dev
```

测试：

```bash
cd /Users/jiaxulong/Documents/smarttraffic/backend
python3 -m pytest tests
```

## 当前 API

- `GET /health`
- `GET /api/config`
- `POST /api/videos/upload`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `POST /api/videos/{video_id}/process`
- `GET /api/videos/{video_id}/status`
- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/detections?limit=100`

## 阶段二产物

```text
results/traffic_analysis/<run_id>/
  metadata.json
  detections.csv
  detections.jsonl
  detection_summary.json
  detection_preview.mp4  # only when requested
  keyframes/
```

## 数据与安全

本地视频默认进入 `local_videos/`，分析结果默认进入 `results/traffic_analysis/<run_id>/`。`local_models/`、`local_videos/`、`results/`、缓存目录、模型权重、大视频和运行结果默认被 `.gitignore` 排除。
