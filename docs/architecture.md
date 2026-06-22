# Architecture

SmartTraffic follows the manual's layered boundary:

```text
React frontend
  -> FastAPI API layer
  -> services
  -> cv / trajectory / events / analysis packages
  -> local storage and future database
```

The current stage-four runnable path is:

```text
video upload
  -> frame reader
  -> YOLOv8 detector
  -> DeepSORT / mock tracker
  -> TrajectoryEngine
  -> artifact writer
  -> FastAPI query
  -> React minimal dashboard
```

Implemented boundaries:

- `backend/app/api`: HTTP routes.
- `backend/app/services`: detection, tracking, trajectory orchestration and in-memory processing registry.
- `backend/app/cv`: frame reader, YOLOv8 detector adapter, video writer, DeepSORT / deterministic mock tracker.
- `backend/app/trajectory`: geometry utilities, trajectory feature helpers, and `TrajectoryEngine`.
- `backend/app/analysis`: artifact writer for run directories, metadata, detections, tracks, and trajectory outputs.
- `frontend/src`: Vite/React pages for video processing and minimal analysis result display.

The current Traffic Analysis Center is primarily artifact-based run result query. It reads local files under `results/traffic_analysis/<run_id>/` and exposes detection, tracking, and trajectory outputs through FastAPI. It is not yet a complete database-backed result center.

The current database layer is not a complete production implementation. Local artifacts are the source of truth for trajectory results at this stage.

Event Engine has not started. Alert Center, Review Center, Bad Case Center, and Evaluation Center are still not completed. Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Review Center, Bad Case Center, and Evaluation Center separate.
