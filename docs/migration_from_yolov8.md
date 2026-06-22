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
| ByteTrack runtime files under `src/tracking/` and tracking CLIs | Current phase forbids full tracker implementation; only a DeepSORT interface placeholder was created. |
| `src/analytics/*` event/counting runtime | Current phase forbids full Trajectory Engine and Event Engine implementation. |
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
