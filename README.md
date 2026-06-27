# SmartTraffic: Intelligent Traffic Event Detection Platform

A local validation platform for traffic video analysis, combining YOLOv8,
DeepSORT, trajectory semantics, configurable event rules, review workflows, Bad
Case tracking, evaluation, and Docker-based delivery.

SmartTraffic 是一个智慧交通事件检测 local validation project，不是普通 YOLOv8
检测框 Demo。

## Project Snapshot

| Item | Status |
| --- | --- |
| Current baseline | `v1.0.1-spec-completion` |
| Project type | Smart traffic event detection local validation platform |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Frontend | React, TypeScript, Vite |
| CV stack | YOLOv8 wrapper, DeepSORT adapter |
| Database | SQLite prototype via SQLAlchemy |
| Delivery | Docker Compose local delivery |
| Event coverage | 6 configurable traffic event rules |
| Evaluation | Local / synthetic validation metrics |
| Boundary | Not production-ready or law-enforcement-grade |

## What Problem It Solves

Object detection answers "what is in the frame". SmartTraffic adds the next
layer: track objects over time, derive trajectory semantics, apply configurable
road-space rules, then make the result reviewable and measurable.

```text
video
-> detection
-> tracking
-> trajectory semantics
-> zone/rule reasoning
-> events
-> evidence
-> alert/review
-> bad case/evaluation
```

## Core Pipeline

```text
Video Upload / Camera Source
  -> YOLOv8 Detection
  -> DeepSORT Tracking
  -> Trajectory Engine
  -> Zone & Rule Config
  -> Event Engine
  -> Alert Center
  -> Traffic Analysis Center
  -> Review / Bad Case / Evaluation
  -> Report Export / Docker Local Delivery
```

## Key Features

### Video Processing

- Local video upload, metadata extraction, validation, and processing task
  lifecycle.
- Run-scoped analysis records so the same video can have multiple local
  validation runs.
- Local artifacts remain in ignored output directories and are not committed.

### Detection And Tracking

- YOLOv8 detector wrapper with deterministic dry-run support for environments
  without local model weights.
- DeepSORT adapter with deterministic mock tracking for repeatable tests.
- Detection and tracking produce structured inputs; event judgment is handled
  by the trajectory and rule layers.

### Trajectory Engine

- Derives pixel speed, moving angle, dwell time, track length, last-seen state,
  and direction consistency.
- Exposes trajectory semantics including `zone_history`, `lane_relation`, and
  `line_crossings`.
- DB-backed `zones` and `event_rules` enter the default processing pipeline when
  configured.
- Pixel speed is a local image-space signal, not calibrated real-world speed.

### Zone & Rule Config

- DB-backed zone and event rule CRUD for local validation.
- Supports polygon zones, direction lines, `counting_zone`, and
  `counting_line` semantics.
- Event rule `severity` uses the `low` / `medium` / `high` contract.
- Alert level is separate and uses `info` / `warning` / `critical`.
- Processing runs keep a config snapshot for reproducibility.

### Event Engine

- Six configurable event rules: wrong-way driving, illegal parking, danger zone
  intrusion, pedestrian in vehicle lane, congestion, and flow counting.
- Persists `event_evidence` and `rule_executions` for review, debugging, and
  evaluation traceability.
- Supports `event_rules_only` rerun using existing trajectory/config data.

### Alert / Review / Bad Case

- Alert Center manages alert status, while Review Center manages event review
  status.
- Review Center supports confirmation, false positive, false negative, ignore,
  resolve, comments, and rerun request recording.
- Evaluation failed cases such as `id_switch` and `track_lost` can be linked
  through failed-case -> Bad Case workflows.

### Evaluation Center

- Local event metrics include `event_accuracy`, `false_alarm_rate`,
  `event_recall`, `event_f1`, and per-event metrics.
- Detection, tracking, trajectory, event, flow-counting, and regression checks
  are scoped to local / synthetic validation data.
- Bad Case regression uses deterministic replay or stored rule replay, not full
  video-level retraining.

### Report / Realtime / Docker

- Report exports cover CSV, JSON, PDF, bundle metadata, keyframe summary, and
  annotated-video references.
- Realtime is a preview metadata workflow for mock, upload, local file, and
  RTSP no-connect scenarios.
- Docker Compose provides the local delivery path for backend, frontend,
  migrations, SQLite, and ignored artifact directories.

## System Architecture

```text
Frontend
  React / TypeScript / Vite
  Dashboard, Analysis Detail, Zone Config, Alert, Review, Bad Case, Evaluation

Backend
  FastAPI
  API Routers -> Services -> Repositories -> SQLAlchemy Models

CV & Analytics
  YOLOv8 Detector
  DeepSORT Tracker
  Trajectory Engine
  Event Engine
  Evaluation Service

Storage
  SQLite Prototype
  Local Artifacts
  Docker-mounted Local Directories
```

## Event Detection Logic

SmartTraffic does not train a dedicated wrong-way, parking, congestion, or
pedestrian-lane model. It detects objects, tracks them, derives trajectory
semantics, and applies configurable rules.

| Event | Rule Basis |
| --- | --- |
| Wrong-way driving | Moving angle vs allowed direction |
| Illegal parking | Low speed + dwell time + no-parking zone |
| Danger zone intrusion | Object bottom-center inside danger zone |
| Pedestrian in vehicle lane | Person inside `vehicle_lane` |
| Congestion | Vehicle count + average speed + time window |
| Flow counting | Track crossing configured counting line |

## API Overview

Full endpoint details are documented in [`docs/api_reference.md`](docs/api_reference.md).

- Health and config: `/health`, `/health/ready`, `/api/config`
- Videos and processing: `/api/videos`, `/api/processing/tasks`
- Analysis runs: `/api/analysis-runs`
- Detection, tracking, and trajectory results: `/api/detections`, `/api/tracks`,
  `/api/trajectories`
- Zones and rules: `/api/zones`, `/api/event-rules`
- Events and alerts: `/api/events`, `/api/alerts`
- Review and Bad Case: `/api/review`, `/api/bad-cases`
- Evaluation and reports: `/api/evaluation`, `/api/reports`
- Camera and realtime preview: `/api/cameras`, `/api/realtime`

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

Docker Compose is the local validation and demo delivery path. It starts the
FastAPI backend at `http://localhost:8000`, the Vite frontend at
`http://localhost:5173`, runs Alembic migrations at backend startup, and stores
SQLite / artifact output in ignored local directories such as `results/`.
For real local YOLOv8 detection, place `yolov8n.pt` in `local_models/` and set
`YOLO_MODEL_PATH=/app/local_models/yolov8n.pt`, `YOLO_DRY_RUN=false`, and
`DEEPSORT_DRY_RUN=true` in the local `.env`.

### One-click Start

Docker Desktop is required. On macOS, double-click
`start_smarttraffic.command`. On Windows, double-click `start_smarttraffic.bat`.
The full beginner guide is in [`docs/one_click_start.md`](docs/one_click_start.md).

## Demo Validation

```bash
python3 scripts/seed_demo_data.py
./backend/.venv/bin/python -m pytest backend/tests/test_seed_demo_data.py -q
```

The demo seed creates local toy config for 4 zones, 6 event rules, and 6
expected event examples. It is synthetic / sample / local validation only. Real
videos, model weights, generated reports, and runtime artifacts are not
committed.

## Validation Status

Latest recorded validation:

| Check | Result |
| --- | --- |
| Git whitespace check | Passed |
| Backend tests | `480 passed, 4 warnings` |
| Frontend tests | `77 passed` |
| Docker Compose config | Passed |
| Docker Compose build | Passed; built `smarttraffic-backend:latest` |
| Danger check | Passed |
| Demo seed test | Passed |
| Tracked forbidden-file scan | Passed |

## Milestones

- `v1.0.0-smarttraffic-final-local-delivery`: first final local delivery
  baseline.
- `v1.0.1-spec-completion`: current spec-complete final local delivery
  baseline.

Earlier v0.9.x and v1.0.x tags are preserved as historical engineering
milestones and are not moved.

## Safety And Data Policy

Do not commit:

- `.env`
- secrets, tokens, passwords, API keys, or real RTSP URLs
- model weights
- large videos or uploaded videos
- generated results, reports, keyframes, or annotated videos
- local DB files such as `.db`, `.sqlite`, or `.sqlite3`
- caches, `dist`, `node_modules`, or virtual environments

## Known Boundaries

- SmartTraffic is a local validation prototype.
- It is not a formal traffic enforcement system.
- It is not production-ready.
- It is not law-enforcement-grade.
- It is not a commercial deployment.
- It is not an official COCO, TrackEval, or real-world traffic benchmark.
- Realtime is preview metadata only.
- Pixel speed is not calibrated real-world speed.
- Bad Case regression is deterministic replay / stored rule replay, not a full
  video-level rerun.
- SQLite and Docker Compose are for local prototype reproducibility.

## Final Status

SmartTraffic `v1.0.1-spec-completion` is the current spec-complete final local
delivery baseline. The repository is closed for the current v1.0 scope. Future
work should move to v1.1 enhancements such as real-video benchmarking,
production deployment hardening, official metric adapters, and stronger
realtime stream support.
