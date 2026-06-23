# Architecture

SmartTraffic follows the manual's layered boundary:

```text
React frontend
  -> FastAPI API layer
  -> services
  -> cv / trajectory / events / alerts / analysis packages
  -> local storage and future database
```

## Current Runnable Path

The current runnable processing path is still detection / tracking / trajectory:

```text
video upload
  -> frame reader
  -> YOLOv8 detector
  -> DeepSORT / mock tracker
  -> TrajectoryEngine
  -> trajectory artifacts
  -> FastAPI query
  -> React minimal dashboard
```

The current process API does not directly run events or alerts. Stage 5 minimal Event & Alert behavior operates on existing local artifacts.

## Stage 5 Minimal Event & Alert Pipeline

The current stage-five artifact path is:

```text
trajectory artifacts
  -> EventService / EventEngine
  -> event artifacts
  -> AlertService
  -> alert artifacts
  -> FastAPI query endpoints
  -> React Analysis Detail minimal view
```

Event artifacts:

- `events.jsonl`
- `event_evidence.jsonl`
- `rule_executions.jsonl`
- `event_summary.json`

Alert artifacts:

- `alerts.jsonl`
- `alert_summary.json`

The current EventService and AlertService form an artifact-based generation and query loop. They are not a complete database-backed result center, and they are not law-enforcement-grade traffic violation judgment.

## Backend Components

- `backend/app/api`: HTTP routes.
- `backend/app/services`: detection, tracking, trajectory orchestration, event generation, alert generation, and in-memory processing registry.
- `backend/app/cv`: frame reader, YOLOv8 detector adapter, video writer, DeepSORT / deterministic mock tracker.
- `backend/app/trajectory`: geometry utilities, trajectory feature helpers, and `TrajectoryEngine`.
- `backend/app/events`: event contracts, evidence helpers, rule execution helpers, `EventEngine`, dedup helpers, and rule callbacks.
- `backend/app/alerts`: minimal alert contract helpers.
- `backend/app/analysis`: artifact writer for run directories, metadata, detections, tracks, trajectory outputs, event outputs, and alert outputs.

Implemented stage-five rule callbacks:

- `danger_zone_intrusion`
- `pedestrian_in_vehicle_lane`
- `illegal_parking`

The `SUPPORTED_EVENT_TYPES` list includes future event types, but `wrong_way_driving`, `congestion`, and `flow_counting` callbacks are not implemented yet.

## Query Layer

The current Traffic Analysis Center is primarily artifact-based run result query. It reads local files under `results/traffic_analysis/<run_id>/` and exposes detection, tracking, trajectory, event, and alert outputs through FastAPI.

Implemented artifact query endpoints include:

- `GET /api/analysis-runs/{run_id}/detections`
- `GET /api/analysis-runs/{run_id}/tracks`
- `GET /api/analysis-runs/{run_id}/trajectory-points`
- `GET /api/analysis-runs/{run_id}/events`
- `POST /api/analysis-runs/{run_id}/alerts/generate`
- `GET /api/analysis-runs/{run_id}/alerts`

The current database layer is not a complete production implementation. Local artifacts are the source of truth for trajectory, event, and alert results at this stage.

## Frontend Components

- `frontend/src/pages/VideoCenterPage.tsx`: upload and process detection / tracking / trajectory modes.
- `frontend/src/pages/AnalysisDetailPage.tsx`: minimal detection, tracking, trajectory, event, and alert query view.
- `frontend/src/pages/AlertCenterPage.tsx` and `frontend/src/components/AlertPanel.tsx`: currently a placeholder shell; the working minimal alert view is in Analysis Detail.

Current frontend limitations:

- no zone editor workflow
- no video overlay for trajectories/events/alerts
- no alert timeline
- no acknowledge / resolve controls
- no review workflow

## Boundaries And Limitations

Current limitations:

- no process mode for events / alerts yet
- no full Alert Center status workflow
- no acknowledge / resolve / ignored status mutation API
- no Review Center workflow
- no Bad Case Center workflow
- no Evaluation Center workflow
- no Zone Editor implementation
- no video overlay
- no `wrong_way_driving`
- no `congestion`
- no `flow_counting`
- no real-world speed calibration
- no formal traffic enforcement conclusion

Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Alert Center, Review Center, Bad Case Center, and Evaluation Center separate.
