# SmartTraffic: Intelligent Traffic Event Detection Platform

YOLOv8 + DeepSORT + Trajectory Engine + Event Engine + FastAPI + React + Database

SmartTraffic is a local, reviewable traffic video analysis platform for the final
SmartTraffic project scope. It connects video upload, object detection,
multi-object tracking, trajectory features, event rules, alert handling,
manual review, Bad Case management, evaluation, report export, and a realtime
preview workflow.

SmartTraffic is a 智慧交通事件检测平台. It is not a traffic enforcement system.

## Project Summary

| Item | Current status |
| --- | --- |
| Project type | Local intelligent traffic event detection and review platform |
| Final implementation tag | `v1.0.3-final-hardening` |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Frontend | React, TypeScript, Vite |
| Detection | YOLOv8 wrapper with deterministic dry-run support |
| Tracking | DeepSORT adapter with deterministic mock tracker |
| Database | SQLite prototype through SQLAlchemy and Alembic |
| Report export | CSV, JSON, PDF, report bundle metadata, keyframe summary, annotated video reference |
| Realtime | Camera and realtime preview only, not production realtime monitoring |
| Final acceptance | Passed under the execution manual's local validation scope |
| Safety boundary | Analysis and review only; not for traffic enforcement |

## What This Project Does

```text
video upload / camera source
  -> metadata extraction
  -> YOLOv8 detection
  -> DeepSORT tracking
  -> trajectory feature extraction
  -> event rule engine
  -> alert generation
  -> traffic analysis run index
  -> dashboard / review / bad case / evaluation
  -> report export
```

Core capabilities:

- Upload and validate local videos, extract metadata, and create processing
  tasks.
- Run YOLOv8 detection or deterministic dry-run detection.
- Run DeepSORT tracking or deterministic mock tracking.
- Derive trajectory features for speed, direction, dwell time, zone membership,
  lane relation, and line crossing.
- Configure zones and event rules with DB-backed CRUD.
- Detect six event types through the Event Engine.
- Generate alerts and manage alert status.
- Review events manually, add comments, mark false positives / false negatives,
  and request rule reruns.
- Convert review or evaluation failures into Bad Cases.
- Run lightweight evaluation workflows for event, flow, trajectory, detection,
  tracking, and regression scenarios.
- Export analysis reports as CSV, JSON, PDF, and bundle metadata.
- Preview camera / realtime metadata for mock, local file, upload placeholder,
  and RTSP no-connect sources.
- Keep explicit security, data, and engineering boundaries for local validation.

## Final Feature Set

### Video And Processing

- Video upload, list, detail, status, and frame metadata query APIs.
- Upload validation for extension, size, OpenCV duration metadata, and codec
  allowlist.
- DB-backed `processing_tasks` lifecycle with status, progress, timestamps, and
  error details.
- DB-backed `traffic_analysis_runs`, allowing multiple runs per video.
- Local artifacts remain under `results/traffic_analysis/<run_id>/`.

### Detection And Tracking

- `YoloDetector` wrapper for YOLOv8 / Ultralytics integration.
- `YOLO_DRY_RUN=true` deterministic detection path for local validation without
  model weights.
- DeepSORT adapter plus deterministic mock tracker.
- DB-backed detections, tracks, and detector / tracker `model_runs` records.
- Detection and tracking produce structured analysis inputs; they do not make
  event judgments.

### Trajectory Engine

- Pixel-space speed, moving angle, direction vector, direction consistency, and
  dwell time.
- Zone history, lane relation, track length, last-seen state, and line crossing
  features.
- Zone membership can use center or bottom-center point strategies.
- Pixel speed is not real-world speed in m/s or km/h.

### Event Engine

Implemented event types:

- `wrong_way_driving`
- `illegal_parking`
- `danger_zone_intrusion`
- `pedestrian_in_vehicle_lane`
- `congestion`
- `flow_counting`

Event rule `severity` is constrained to `low`, `medium`, or `high`. The Event
Engine consumes trajectory features plus zones / rules; it does not run model
inference directly.

### Zone And Rule Configuration

- DB-backed `/api/zones` and `/api/event-rules` CRUD.
- ZoneEditor supports polygon drawing, direction line drawing, counting line
  drawing, save / update / delete, enabled state, version display, and
  validation.
- Processing runs store a run-level zone / rule config snapshot for
  reproducibility.
- Geometry is pixel-space local validation, not calibrated road mapping.

### Alert Center

- Alerts can be `new`, `acknowledged`, `resolved`, or `ignored`.
- Alert Center `level` is separate from event rule `severity`; alert level may
  be `info`, `warning`, or `critical`.
- Run-level alert reads are DB-first when DB rows exist and fall back to local
  artifacts for older runs.

### Review And Bad Case

- Review workflows support confirm, false positive, false negative, ignore,
  resolve, comments, Review -> Bad Case, and rule-rerun request recording.
- Review actions append audit records for DB-backed events and preserve
  artifact fallback for legacy runs.
- Bad Case workflows support create, update, list, detail, summary, from-review,
  and from-failed-case.
- Failed evaluation cases can be converted into Bad Cases explicitly.

### Evaluation Center

- Event metrics use frame-range overlap / tolerance matching.
- Flow counting metrics compare expected and actual counts.
- Trajectory metrics summarize track count, trajectory point count, average
  track length, average speed, and direction availability.
- Detection metrics are VOC-style single-IoU AP / mAP, precision, recall, and
  per-class AP when annotations exist.
- Tracking metrics are lightweight deterministic IDF1 / MOTA / ID switch /
  track-lost calculations.
- Bad Case regression uses deterministic replay / stored rule replay. It is not
  a full video-level rerun.

### Report Center

- Report run list and run summary.
- CSV exports for events, alerts, flow counts, zone statistics, bad cases, and
  evaluation results.
- Structured JSON export.
- Lightweight in-memory PDF export.
- Report bundle metadata with keyframe summary and annotated video reference.
- Report output is for analysis and review only, not for traffic enforcement.

### Camera And Realtime Preview

- DB-backed camera CRUD, enable, and disable.
- Camera source types: `upload`, `rtsp`, `file`, and `mock`.
- `stream_url` is stored for local configuration but API responses expose only
  `masked_stream_url`.
- Mock stream preview, local file smoke-level preview, upload placeholder
  metadata, and RTSP no-connect preview.
- Recent frames, events, and alerts are kept in a bounded in-memory preview
  cache.
- Start creates `processing_tasks.mode=realtime_process`.
- This is realtime preview metadata, not production realtime monitoring.

### Security And Ops

- Minimal actor headers: `X-SmartTraffic-Actor` and `X-SmartTraffic-Role`.
- `SMARTTRAFFIC_AUTH_MODE=permissive|strict`.
- Preview roles: `viewer`, `operator`, `reviewer`, `admin`.
- Actor propagation for alert, review, event, Bad Case, realtime, and rule-rerun
  actions.
- Standard API error shape with `error_code`, `message`, `detail`, and
  `request_id`.
- Request id logging and `GET /health/ready` DB readiness check.
- RTSP / secret-like values are redacted or masked in responses and errors.

## System Architecture

```text
Frontend
  React + TypeScript + Vite
  Dashboard / Video Center / Analysis Detail / Zone & Rules
  Alert Center / Review Center / Bad Case Center
  Evaluation Center / Report Center / Camera Center

Backend
  FastAPI routers
  Services
  Repositories
  SQLAlchemy models
  Alembic migrations

CV And Analytics
  YOLOv8 Detector
  DeepSORT Tracker
  Trajectory Engine
  Event Engine
  Alert Service
  Evaluation Service

Storage
  SQLite prototype
  Local artifacts
  Results directory
  Local-only models and videos
```

The backend registers routers for health, cameras, videos, processing,
detections, tracks, trajectories, events, event rules, alerts, zones, analysis
runs, review, bad cases, evaluation, reports, and realtime preview.

## Database And Artifacts

SmartTraffic uses a DB-first / artifact-fallback model for local validation.
Current SQLAlchemy / Alembic tables cover videos, cameras, frames, detections,
tracks, trajectory points, events, event evidence, alerts, event rules, zones,
flow counts, zone statistics, processing tasks, traffic analysis runs, rule
executions, review comments, bad cases, evaluation datasets, evaluation
results, and model runs.

Important prototype boundaries:

- The default database is local SQLite via `SMARTTRAFFIC_DATABASE_URL`.
- The `frames` table / API is a frame metadata and query contract. The pipeline
  does not persist every frame image by default.
- `tracks` are run-level track records plus metadata / artifact-compatible rows.
  This is not a production per-frame normalized tracking table.
- Local artifacts may include metadata, detections, tracks, trajectory points,
  events, evidence, rule executions, alerts, flow counts, zone statistics,
  review records, bad cases, evaluation summary, keyframe references, and
  annotated video references.
- Generated videos, keyframes, results, local DB files, model weights, and
  uploaded videos must stay out of Git.

## API Overview

Full endpoint details are documented in
[`docs/api_reference.md`](docs/api_reference.md).

Main API groups:

- Health / readiness / config: `/health`, `/health/ready`, `/api/config`
- Videos and processing: `/api/videos`, `/api/processing/tasks`
- Analysis runs: `/api/analysis-runs`
- Detection / tracking / trajectory query placeholders: `/api/detections`,
  `/api/tracks`, `/api/trajectories`
- Zones and event rules: `/api/zones`, `/api/event-rules`
- Events and alerts: `/api/events`, `/api/alerts`
- Review: `/api/review`
- Bad cases: `/api/bad-cases`
- Evaluation: `/api/evaluation`
- Reports: `/api/reports`
- Cameras and realtime preview: `/api/cameras`, `/api/realtime`

## Frontend Pages

- Dashboard
- Camera Center
- Video Center
- Analysis Detail
- Zone & Rule Config
- Alert Center
- Review Center
- Bad Case Center
- Evaluation Center
- Report Center

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
docker compose config
docker compose up
```

### Demo Data

```bash
python3 scripts/seed_demo_data.py
```

The demo seed script creates small sample config and toy expected files. It does
not add real videos, model weights, or generated result artifacts.

## Environment Variables

Key local settings from [`.env.example`](.env.example):

- `SMARTTRAFFIC_DATABASE_URL`
- `SMARTTRAFFIC_RESULTS_DIR`
- `SMARTTRAFFIC_LOCAL_VIDEOS_DIR`
- `SMARTTRAFFIC_LOCAL_MODELS_DIR`
- `SMARTTRAFFIC_AUTH_MODE`
- `SMARTTRAFFIC_MAX_UPLOAD_MB`
- `SMARTTRAFFIC_MAX_VIDEO_DURATION_SECONDS`
- `SMARTTRAFFIC_ALLOWED_VIDEO_CODECS`
- `YOLO_MODEL_PATH`
- `YOLO_DRY_RUN`
- `YOLO_CONF_THRESHOLD`
- `YOLO_IOU_THRESHOLD`
- `YOLO_DEVICE`
- `DEEPSORT_DRY_RUN`

Copy `.env.example` to `.env` for local overrides. `.env` must not be committed.

## Validation

Final v1.0.3 validation was completed under the execution manual scope:

| Check | Result |
| --- | --- |
| Backend pytest | `472 passed, 4 warnings` |
| Frontend Node tests | `77 passed` |
| Frontend build | Passed |
| Alembic upgrade / downgrade / upgrade | Passed |
| `docker compose config` | Passed |
| `python3 scripts/danger_check.py` | Passed |
| `python3 scripts/run_evals.py --help` | Passed |
| `make docker-config` / `make danger-check` | Passed |

This README polish is documentation-only and does not move the final
implementation tag.

## Milestones

Important preserved tags:

- `v0.9.0-final-engineering-delivery`
- `v0.9.1-db-foundation`
- `v0.9.2-db-backed-core-flow`
- `v0.9.3-quality-db-flow`
- `v0.9.4-real-evaluation`
- `v0.9.5-frontend-complete`
- `v0.9.6-report-center`
- `v0.9.7-realtime-security-preview`
- `v1.0.0-full-final-version`
- `v1.0.1-audit-polish`
- `v1.0.2-spec-alignment`
- `v1.0.3-final-hardening`

Old tags are preserved and must not be moved. The final display version is
`v1.0.3-final-hardening`.

## Safety And Data Policy

Do not commit:

- `.env`
- secrets, tokens, passwords, API keys, or real RTSP URLs
- model weights
- large videos or uploaded videos
- generated results, reports, keyframes, or annotated videos
- local DB files such as `.db`, `.sqlite`, or `.sqlite3`
- caches, `dist`, `node_modules`, or virtual environments

The repository keeps only code, docs, tiny sample config, toy expected files,
and placeholder `.gitkeep` files needed for reproducibility.

## Known Boundaries

- SmartTraffic is not a traffic enforcement system.
- Realtime is preview metadata, not production realtime monitoring.
- Minimal actor identity is not production IAM.
- Detection mAP is VOC-style single-IoU, not COCO official mAP.
- Tracking IDF1 / MOTA are lightweight deterministic metrics, not TrackEval
  official implementation.
- Bad Case regression is deterministic replay / stored rule replay, not a full
  video-level rerun.
- SQLite and Docker Compose are for local prototype reproducibility.
- Frames and tracks use metadata / artifact-compatible local prototype
  granularity.
- Pixel-space speed, direction, zone, and line-crossing logic are not
  real-world calibrated traffic engineering measurements.

## Final Status

SmartTraffic is frozen at `v1.0.3-final-hardening`.

Development is closed. Future work should focus on documentation screenshots,
demo materials, resume bullets, and interview explanation.
