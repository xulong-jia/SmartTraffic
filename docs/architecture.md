# Architecture

SmartTraffic follows the manual's layered boundary:

```text
React frontend
  -> FastAPI API layer
  -> services
  -> cv / trajectory / events / alerts / analysis packages
  -> local artifacts and DB-backed workflow foundation
```

## Current Runnable Path

The current runnable processing path can run detection / tracking / trajectory
and then generate event, traffic statistics, alert, and visual artifacts:

```text
video upload
  -> frame reader
  -> YOLOv8 detector
  -> DeepSORT / mock tracker
  -> TrajectoryEngine
  -> trajectory artifacts
  -> EventService / EventEngine
  -> event artifacts
  -> traffic statistics artifacts
  -> AlertService
  -> alert artifacts
  -> visual artifacts
  -> FastAPI query
  -> React Dashboard / Analysis Detail MVP
```

The current process API runs EventService, the Stage 6C statistics writer,
AlertService, and the Stage 6F visual artifacts writer after
`mode=detection_tracking_trajectory`. Empty `event_rules` / `zones` produce
stable empty event, statistics, alert, and visual artifacts rather than fake
events.

## Docker Local Delivery

Docker Compose is used for local validation and demo delivery. The backend
image runs Alembic migrations before starting FastAPI, the frontend service
runs the Vite dev server, and both services use local SQLite plus mounted
directories for videos, models, results, samples, and evaluation inputs.

This Docker path is not a production deployment boundary. It exists to make the
local prototype reproducible without committing videos, model weights, local
databases, or generated result artifacts.

## Current Implemented Architecture

Currently implemented architecture includes:

- YOLOv8 / dry-run detection
- DeepSORT adapter / mock tracking
- TrajectoryEngine with Full Stage 4AB final features
- EventEngine with six finalized callback-based rules
- artifact-based EventService
- artifact-based AlertService
- process integration for event, traffic statistics, and alert artifact
  generation after trajectory
- Stage 6F `keyframes/index.json`, keyframe snapshot, and
  `annotated_video.mp4` visual artifact pipeline with controlled fallback
  statuses
- artifact-backed Analysis Runs list / summary API with directory scan fallback
- Stage 6E frontend Dashboard / Video Center / Analysis Detail real run data MVP
- Stage 6 Traffic Analysis Center artifact-based MVP
- minimal frontend tables in Analysis Detail and Alert Center
- Stage 7C artifact-backed Review API MVP
- Stage 7D React Review Center MVP for review filters, event list/detail,
  review actions, comments, and false-negative records
- Stage 7E minimal URL navigation from Analysis Detail and Alert Center into
  Review Center without alert/review status auto-sync
- Stage 7F closeout audit confirming the local artifact-backed Review Center
  MVP boundary
- Stage 8B artifact-backed Bad Case schema, JSONL artifacts, service methods,
  manifest / metadata / artifact index summaries, and backend tests
- Stage 8CD artifact-backed Bad Case API and React Bad Case Center MVP for
  filters, list/detail, create, update, summary, and from-review creation
- Stage 8EFG artifact-backed Evaluation datasets, runs, results, failed cases,
  `evaluation_summary.json`, MVP metrics, API, CLI, and React Evaluation Center
- Stage 8HI failed case to Bad Case conversion, Bad Case regression summary
  MVP, frontend link action, and Stage 8 closeout audit
- Full Stage 4AB trajectory final features: zone history, lane relation, line
  crossings, dwell/speed/moving-angle/direction-consistency features, and
  center / bottom-center point strategies
- Full Stage 4AB event rule finalization for wrong-way, illegal parking, danger
  zone intrusion, pedestrian in vehicle lane, congestion, and flow counting

The current implementation is useful for local validation, but it is not the
complete production benchmark or enforcement architecture yet.

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

The current EventService and AlertService form an artifact-compatible
generation, query, and alert status loop. Current DB-backed workflows persist
events, evidence, rule executions, alerts, review audit records, Bad Cases, and
Evaluation results when DB rows are available, while preserving artifact
fallback for legacy runs. They are not law-enforcement-grade traffic violation
judgment.

## Manual Architecture Alignment

The execution manual targets a layered, reviewable, DB-backed local validation
system. Current alignment status:

- Traffic Analysis Center core index and result reads are DB-first with
  artifact fallback.
- Alert Center status workflow is DB-first with artifact fallback.
- Review Center workflow writes DB audit records for DB events and preserves
  artifact fallback.
- Bad Case Center and Evaluation Center are DB-first with artifact fallback.
- Zone / Event Rule config is DB-backed and connected to the ZoneEditor.
- Flow counts and zone statistics are persisted and read DB-first with artifact
  fallback.

These modules are complete for the current local validation scope. They are not
production deployment, enforcement, IAM, or calibrated traffic engineering
systems.

## Backend Components

- `backend/app/api`: HTTP routes.
- `backend/app/services`: detection, tracking, trajectory orchestration, event generation, alert generation, and in-memory processing registry.
- `backend/app/cv`: frame reader, YOLOv8 detector adapter, video writer, DeepSORT / deterministic mock tracker.
- `backend/app/trajectory`: geometry utilities, trajectory feature helpers, and `TrajectoryEngine`.
- `backend/app/events`: event contracts, evidence helpers, rule execution helpers, `EventEngine`, dedup helpers, and rule callbacks.
- `backend/app/alerts`: minimal alert contract helpers.
- `backend/app/analysis`: artifact writer for run directories, metadata, Stage 6B `manifest.json` / `artifact_index.json`, detections, tracks, trajectory outputs, event outputs, traffic statistics outputs, alert outputs, Stage 6F visual artifacts, Stage 7 review artifacts, Stage 8B/8CD/HI Bad Case artifacts, and Stage 8EFG/HI Evaluation artifacts / MVP metrics.

Implemented stage-five rule callbacks:

- `danger_zone_intrusion`
- `pedestrian_in_vehicle_lane`
- `illegal_parking`
- `wrong_way_driving`
- `flow_counting`
- `congestion`

The current `flow_counting` callback is a finalized event rule. It consumes
TrajectoryEngine `line_crossings` when available and keeps the older EventEngine
callback-state fallback for artifact compatibility.

The current `congestion` callback uses aggregate event rule support. EventEngine
calls each aggregate rule once per frame, passes the full
`frame_result["trajectory_points"]`, and emits a zone-level event with
`track_id=None`. The callback uses EventEngine state to maintain consecutive
congestion-frame and time-window counts; EventEngine aggregate cooldown and
dedup handle repeated zone-level events.

## Query Layer

The current Traffic Analysis Center is DB-first with artifact fallback for the
core local validation workflow. It reads `traffic_analysis_runs`, detections,
tracks, trajectory points, flow counts, zone statistics, events, alerts, Bad
Cases, and Evaluation rows when available, while preserving local files under
`results/traffic_analysis/<run_id>/` for legacy artifact-only runs and visual
references.

Implemented artifact query endpoints include:

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/manifest`
- `GET /api/analysis-runs/{run_id}/detections`
- `GET /api/analysis-runs/{run_id}/tracks`
- `GET /api/analysis-runs/{run_id}/trajectory-points`
- `GET /api/analysis-runs/{run_id}/events`
- `GET /api/analysis-runs/{run_id}/flow-counts`
- `GET /api/analysis-runs/{run_id}/zone-statistics`
- `POST /api/analysis-runs/{run_id}/alerts/generate`
- `GET /api/analysis-runs/{run_id}/alerts`

Stage 6B manifest/index support, Stage 6C statistics support, and Stage 6D
Analysis Runs list / summary support remain artifact-compatible. The list API
can summarize runs from DB, manifest, metadata, artifact index, in-memory
registry, or directory scan fallback. Stage 6E frontend views consume these
APIs for run counts, artifact status, event/alert tables, minimal flow / zone
statistics tables, and visual artifact status. Stage 6F visual artifacts are
local files tracked through manifest / artifact index / metadata; failed visual
generation is reflected as artifact status. The current database layer is a
local SQLite prototype / validation foundation, not a production deployment.

## Frontend Components

- `frontend/src/pages/DashboardPage.tsx`: run count, status distribution, artifact status summary, and recent runs from the Analysis Runs API.
- `frontend/src/pages/VideoCenterPage.tsx`: upload and process detection / tracking / trajectory modes, plus recent analysis runs.
- `frontend/src/pages/AnalysisDetailPage.tsx`: run summary, metadata / manifest / artifact index status, artifact summary, visual artifact status, detection, tracking, trajectory, event, alert, flow count, zone statistics query view, and event Review links.
- `frontend/src/pages/AlertCenterPage.tsx`: minimal alert query and status workflow plus linked event Review links.
- `frontend/src/pages/ReviewCenterPage.tsx`: artifact-backed review event filters, URL query initialization, list/detail, comments, review actions, linked alert display, visual artifact references, and false-negative MVP form.
- `frontend/src/pages/BadCaseCenterPage.tsx`: Stage 8CD/HI artifact-backed Bad Case filters, list/detail, create form, status/root-cause/tag update, source display, linked failed case display, and summary cards.
- `frontend/src/pages/EvaluationCenterPage.tsx`: Stage 8EFG/HI artifact-backed Evaluation dataset registry, run trigger, run/result tables, failed case conversion action, Bad Case regression summary, and summary view.

Current frontend limitations:

- no frontend flow statistics or congestion charting beyond summary/table
  views
- no calibrated traffic engineering dashboard
- no production realtime monitoring UI
- no complex video overlay editor beyond current inspection overlays
- review actions are explicit workflows, not automatic enforcement decisions

## Boundaries And Limitations

Current limitations:

- no complete video-level Bad Case rerun pipeline; current regression is
  deterministic replay / stored rule replay
- no COCO official mAP; current detection mAP is VOC-style single-IoU
- no TrackEval official IDF1 / MOTA; current tracking metrics are lightweight
  deterministic association
- no frontend flow statistics chart
- no frontend congestion chart
- no real-world speed / direction calibration
- no production IAM, central audit storage, monitoring, backup, or deployment
  hardening
- no production realtime monitoring
- no formal traffic enforcement conclusion

Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Alert Center, Review Center, Bad Case Center, and Evaluation Center separate. Full Stage 3 has added DB-backed workflow foundations for Review, Bad Case, and Evaluation while preserving artifact fallback. Full Stage 4AB has finalized trajectory features and event-rule behavior, but it does not imply real detection/tracking benchmarks, real rerun-based regression, real-world calibration, production enforcement readiness, or industrial mAP / IDF1 / MOTA completion.
