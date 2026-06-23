# Migration From YOLOv8 Project

Source project:

`/Users/jiaxulong/Documents/yolov8-vehicle-pedestrian-detection`

The source project was inspected in read-only mode. No files were modified, moved, or deleted.

## Migrated And Refactored

| Source | SmartTraffic target | Action |
| --- | --- | --- |
| `src/core/config.py` | `backend/app/core/config.py` | Migrated environment-backed configuration ideas and renamed variables to SmartTraffic semantics. |
| `src/core/model_loader.py` and `src/services/image_inference_service.py` | `backend/app/cv/yolo_detector.py` | Migrated lazy model loading and detection formatting into `YoloDetector`; dry-run is enabled by default. |
| `src/video_reader.py` | `backend/app/cv/frame_reader.py` | Migrated OpenCV metadata reading and renamed fields to `total_frames` and `duration_seconds`. |
| `src/tracking/track_writer.py` and `src/services/video_analysis_center.py` | `backend/app/analysis/artifact_writer.py` | Migrated result directory and `metadata.json` writing pattern for `results/traffic_analysis/<run_id>/`. |
| `frontend/package.json` and Vite structure | `frontend/` | Reused Vite/React/TypeScript setup, rewritten for SmartTraffic page/module names. |
| `Dockerfile`, `Makefile`, `requirements*.txt` | `backend/Dockerfile`, `Makefile`, `backend/requirements.txt` | Reused development workflow ideas and removed old project-specific commands. |

## Not Migrated

| Source area | Reason |
| --- | --- |
| `local_weights/`, `local_videos/`, `local_outputs/`, `runs/`, generated `results/` | Large/local artifacts are excluded by policy. |
| `dataset/train`, `dataset/valid`, `dataset/test` | Dataset splits are outside phase-one initialization and may be large. |
| `app.py` and `app/streamlit_video_demo.py` | Streamlit demo is not part of the new SmartTraffic architecture. |
| ByteTrack runtime files under `src/tracking/` and tracking CLIs | SmartTraffic stage three uses a new DeepSORT adapter boundary instead of directly migrating the old ByteTrack runtime. |
| `src/analytics/*` event/counting runtime | SmartTraffic implements new trajectory, event, and alert layers with its own contracts instead of directly migrating the old analytics runtime. |
| Bad Case and evaluation services/docs as implemented in the old project | SmartTraffic will implement these later under its own Review/Bad Case/Evaluation Center boundaries. |
| Old README product claims and release history | New README must reflect SmartTraffic scope and phase-one status. |
| `frontend/dist`, `frontend/node_modules`, `.pytest_cache`, `__pycache__` | Generated caches/build outputs are not migrated. |

## Notes

The migration keeps only reusable contracts and infrastructure. SmartTraffic remains aligned with the final execution manual and avoids carrying over YOLO demo-specific naming, Streamlit UI, ByteTrack-specific runtime, or completed-project claims.

## Stage 2 YOLOv8 Detection Migration

Stage two expands the earlier detector contract into a runnable SmartTraffic detection pipeline.

Migrated or reworked from the old project:

- Lazy YOLO model loading and optional `ultralytics.YOLO` inference were kept, but moved behind `backend/app/cv/yolo_detector.py`.
- Image/video inference output normalization was rewritten into the SmartTraffic contract: `frame_index`, `timestamp_ms`, `class_name`, `class_id`, `confidence`, `bbox`.
- OpenCV metadata and frame iteration were adapted into `backend/app/cv/frame_reader.py` with `frame_stride` and `max_frames`.
- Result writing ideas from the old Video Analysis Center were narrowed to stage-two artifacts: `detections.csv`, `detections.jsonl`, `detection_summary.json`, and `metadata.json`.

Not migrated:

- Streamlit demo UI and old YOLO demo page copy.
- ByteTrack runtime, tracking CLIs, and tracked video analytics.
- Old event/counting/ROI analytics runtime.
- Old Bad Case and Evaluation implementation.
- Model weights, local videos, generated results, caches, and local outputs.

Boundary difference:

SmartTraffic `YoloDetector` only performs detection and detection-format conversion. It does not create events, run tracking, calculate trajectories, write database rows, or decide alerts. Those responsibilities remain reserved for later SmartTraffic phases.

## Stage 3 DeepSORT Tracking Layer

Stage three is not a direct migration of the old YOLOv8 project's tracking runtime. It adds a new SmartTraffic tracking layer after the stage-two detector contract.

What changed:

- YOLOv8 still only produces frame-level `detections`.
- `backend/app/cv/deepsort_tracker.py` now owns the SmartTraffic tracking contract and `track_id` assignment.
- The default tracker path is deterministic dry-run matching so tests and local development do not need real DeepSORT weights, GPU, network, or ReID embeddings.
- Real DeepSORT is optional through `deep-sort-realtime` if it is available in the environment.
- `backend/app/services/tracking_service.py` orchestrates detection -> tracking and writes `tracks.csv`, `tracks.jsonl`, and `tracking_summary.json`.

Still not migrated or implemented:

- Old event/counting/ROI analytics runtime.
- Event Engine rules.
- Alert, Review, Bad Case, and Evaluation Center complete logic.

Boundary difference:

SmartTraffic DeepSORT tracking is responsible for track identity only. It does not calculate speed, direction, dwell time, zone interactions, traffic violations, or alert decisions.

## Stage 4 Trajectory Engine Layer

Stage four is not a direct migration of the old YOLOv8 project's analytics or counting runtime. The old project primarily provided the detection base and video processing experience. SmartTraffic adds Trajectory Engine as a new engineering layer with its own contracts, tests, artifacts, service pipeline, API, and frontend minimum view.

What changed:

- Trajectory Engine depends on stage-three tracks, not directly on raw detection bbox rows.
- The input contract is `track_id` plus track bbox / center / state over time.
- `backend/app/trajectory/geometry.py` owns reusable geometry helpers.
- `backend/app/trajectory/features.py` converts track points into trajectory features.
- `backend/app/trajectory/engine.py` maintains per-track state and converts frame-level tracks into `trajectory_points`.
- `backend/app/services/trajectory_service.py` orchestrates detection -> tracking -> trajectory and writes stage-four artifacts.
- `GET /api/analysis-runs/{run_id}/trajectory-points` exposes trajectory outputs from local artifacts.

Generated trajectory features include:

- `speed_px_per_frame`
- `speed_px_per_second`
- `direction_vector`
- `moving_angle`
- `track_length`
- `dwell_time_ms`

Still not migrated or implemented:

- Old event/counting/ROI analytics runtime.
- Event/counting implementations from the old project.
- Reverse driving, congestion, and flow-counting rules.
- Full Alert, Review, Bad Case, and Evaluation Center logic.

Boundary difference:

SmartTraffic Trajectory Engine converts `track_id` + center / bbox history into pixel-level trajectory features. It does not decide traffic events or alerts. `speed_px_per_second` is a pixel-level estimate based on timestamp or fps, not real-world speed in m/s or km/h.

## Stage 5 Event And Alert Minimal Pipeline

Stage five is not a direct migration of the old YOLOv8 project's analytics runtime. SmartTraffic adds a new Event Engine and minimal Alert Center layer on top of trajectory artifacts.

What changed:

- `backend/app/events/` owns event contracts, evidence contracts, rule execution contracts, `EventEngine`, dedup helpers, and rule callbacks.
- Implemented rule callbacks are `danger_zone_intrusion`, `pedestrian_in_vehicle_lane`, and `illegal_parking`.
- `backend/app/services/event_service.py` reads existing `trajectory_points.jsonl` artifacts and writes event artifacts.
- `backend/app/alerts/contracts.py` defines the minimal alert contract and severity-to-level mapping.
- `backend/app/services/alert_service.py` reads existing `events.jsonl` artifacts and writes alert artifacts.
- `GET /api/analysis-runs/{run_id}/events` exposes event outputs from local artifacts.
- `POST /api/analysis-runs/{run_id}/alerts/generate` generates alert artifacts from event artifacts.
- `GET /api/analysis-runs/{run_id}/alerts` exposes alert outputs from local artifacts.

Still not migrated or implemented:

- Old event/counting/ROI analytics runtime.
- `wrong_way_driving`.
- `congestion`.
- `flow_counting`.
- Full alert lifecycle mutation such as acknowledge / resolve.
- Review, Bad Case, and Evaluation Center complete logic.
- Real-world speed calibration.
- Law-enforcement-grade traffic violation judgment.

Boundary difference:

SmartTraffic Event Engine and AlertService convert local trajectory and event artifacts into traffic intelligence outputs. They do not call YOLOv8 directly, do not replace the Trajectory Engine, and do not make formal enforcement decisions.
