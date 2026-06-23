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

The current runnable processing path can run detection / tracking / trajectory
and then generate event / alert artifacts:

```text
video upload
  -> frame reader
  -> YOLOv8 detector
  -> DeepSORT / mock tracker
  -> TrajectoryEngine
  -> trajectory artifacts
  -> EventService / EventEngine
  -> event artifacts
  -> AlertService
  -> alert artifacts
  -> FastAPI query
  -> React minimal dashboard
```

The current process API runs EventService and AlertService after
`mode=detection_tracking_trajectory`. Empty `event_rules` / `zones` produce
stable empty event and alert artifacts rather than fake events.

## Current Implemented Architecture

Currently implemented architecture includes:

- YOLOv8 / dry-run detection
- DeepSORT adapter / mock tracking
- TrajectoryEngine
- EventEngine with six callback-based rules
- artifact-based EventService
- artifact-based AlertService
- process integration for event and alert artifact generation after trajectory
- minimal frontend tables in Analysis Detail and Alert Center

The current implementation is useful for local validation, but it is not the
complete database-backed manual architecture yet.

## Stage 5 Event & Alert MVP

The current stage-five artifact path is:

```text
trajectory artifacts
  -> EventService / EventEngine
  -> event artifacts
  -> AlertService
  -> alert artifacts
  -> FastAPI query and alert status endpoints
  -> React Analysis Detail / Alert Center minimal views
```

Event artifacts:

- `events.jsonl`
- `event_evidence.jsonl`
- `rule_executions.jsonl`
- `event_summary.json`

Alert artifacts:

- `alerts.jsonl`
- `alert_summary.json`

The current EventService and AlertService form an artifact-based generation,
query, and alert status loop. They are not a complete database-backed result
center, and they are not law-enforcement-grade traffic violation judgment.

## Planned Manual Architecture

The execution manual still targets:

- database-backed Traffic Analysis Center
- database-backed Alert Center
- Review Center
- Bad Case Center
- Evaluation Center
- persisted Zone & Rule Config beyond the current in-memory MVP
- aggregate flow counting and zone statistics

These modules are not complete in the current project state.

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
- `wrong_way_driving`
- `flow_counting`
- `congestion`

The current `flow_counting` callback is a Stage 5 event rule. It uses
EventEngine callback state to maintain `previous_points` and `counted_keys`
while evaluating whether track segments cross `rule.parameters.line`.

The current `congestion` callback uses aggregate event rule support. EventEngine
calls each aggregate rule once per frame, passes the full
`frame_result["trajectory_points"]`, and emits a zone-level event with
`track_id=None`. The callback uses EventEngine state to maintain consecutive
congestion-frame counts; EventEngine aggregate cooldown and dedup handle
repeated zone-level events.

## Query Layer

The current Traffic Analysis Center is primarily artifact-based run result query. It reads local files under `results/traffic_analysis/<run_id>/` and exposes detection, tracking, trajectory, event, and alert outputs through FastAPI.

This partially overlaps with the execution manual's Stage 6 Traffic Analysis
Center, but it is not a complete database-backed result center.

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
- `frontend/src/pages/AlertCenterPage.tsx`: minimal alert query and status workflow.

Current frontend limitations:

- no zone editor workflow
- no video overlay for trajectories/events/alerts
- no alert timeline
- no review workflow

## Boundaries And Limitations

Current limitations:

- no Review Center workflow
- no Bad Case Center workflow
- no Evaluation Center workflow
- no database-backed Zone / Rule / Alert persistence
- no video overlay
- no complete Traffic Analysis Center
- no `flow_counts` or `zone_statistics` output generation
- no `/api/analysis-runs/{run_id}/flow-counts`
- no `/api/analysis-runs/{run_id}/zone-statistics`
- no frontend flow statistics view
- no frontend congestion chart
- no database-backed zone statistics persistence
- no real-world speed / direction calibration
- no formal traffic enforcement conclusion

Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Alert Center, Review Center, Bad Case Center, and Evaluation Center separate.
