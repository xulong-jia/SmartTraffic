# SmartTraffic 智慧交通事件检测系统

SmartTraffic 是面向交通视频离线分析的智慧交通事件检测系统。当前仓库处于阶段一：项目骨架与视频管理准备，重点是 FastAPI 后端、React 前端、视频元数据读取、处理任务记录、YOLOv8 检测适配器契约和 Traffic Analysis Center 结果目录契约。

## 项目边界

- 当前不实现完整 DeepSORT、Trajectory Engine、Event Engine、Review Center、Bad Case Center 或 Evaluation Center。
- YOLOv8 检测适配器只负责模型加载和检测结果格式化，不判断交通事件。
- 事件结果不作为正式交通执法依据。
- 模型权重、大视频、本地输出结果和缓存文件不提交到 Git。

## 技术栈

- Backend: FastAPI, Pydantic, OpenCV, pytest
- CV: YOLOv8 adapter contract, dry-run by default
- Frontend: React, TypeScript, Vite
- Storage: local files for phase-one prototype artifacts

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

## 数据与安全

本地视频默认进入 `local_videos/`，分析结果默认进入 `results/traffic_analysis/<run_id>/`。`local_models/`、`local_videos/`、`results/`、缓存目录和模型权重默认被 `.gitignore` 排除。
