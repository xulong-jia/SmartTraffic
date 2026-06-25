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

## Current Implemented Architecture

Currently implemented architecture includes:

- YOLOv8 / dry-run detection
- DeepSORT adapter / mock tracking
- TrajectoryEngine
- EventEngine with six callback-based rules
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
- database-backed flow counting and zone statistics

These modules are not complete in the current project state.

## Backend Components

- `backend/app/api`: HTTP routes.
- `backend/app/services`: detection, tracking, trajectory orchestration, event generation, alert generation, and in-memory processing registry.
- `backend/app/cv`: frame reader, YOLOv8 detector adapter, video writer, DeepSORT / deterministic mock tracker.
- `backend/app/trajectory`: geometry utilities, trajectory feature helpers, and `TrajectoryEngine`.
- `backend/app/events`: event contracts, evidence helpers, rule execution helpers, `EventEngine`, dedup helpers, and rule callbacks.
- `backend/app/alerts`: minimal alert contract helpers.
- `backend/app/analysis`: artifact writer for run directories, metadata, Stage 6B `manifest.json` / `artifact_index.json`, detections, tracks, trajectory outputs, event outputs, traffic statistics outputs, alert outputs, Stage 6F visual artifacts, Stage 7 review artifacts, Stage 8B/8CD Bad Case artifacts, and Stage 8EFG Evaluation artifacts / MVP metrics.

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

The current Traffic Analysis Center is an artifact-based run result query MVP.
It reads local files under `results/traffic_analysis/<run_id>/` and exposes
detection, tracking, trajectory, event, traffic statistics, alert, and visual
artifact status through FastAPI.

This satisfies the current Stage 6 MVP boundary, but it is not a complete
database-backed result center.

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
Analysis Runs list / summary support are still artifact-backed. The list API can
summarize runs from manifest, metadata, artifact index, in-memory registry, or
directory scan fallback. Stage 6E frontend views consume these APIs for run
counts, artifact status, event/alert tables, minimal flow / zone statistics
tables, and visual artifact status. Stage 6F visual artifacts are local files
tracked through manifest / artifact index / metadata; failed visual generation
is reflected as artifact status rather than turning the run into a database
workflow. The current database layer is not a complete production
implementation. Local artifacts are the source of truth for trajectory, event,
traffic statistics, alert, and visual review results at this stage.

## Frontend Components

- `frontend/src/pages/DashboardPage.tsx`: run count, status distribution, artifact status summary, and recent runs from the Analysis Runs API.
- `frontend/src/pages/VideoCenterPage.tsx`: upload and process detection / tracking / trajectory modes, plus recent analysis runs.
- `frontend/src/pages/AnalysisDetailPage.tsx`: run summary, metadata / manifest / artifact index status, artifact summary, visual artifact status, detection, tracking, trajectory, event, alert, flow count, zone statistics query view, and event Review links.
- `frontend/src/pages/AlertCenterPage.tsx`: minimal alert query and status workflow plus linked event Review links.
- `frontend/src/pages/ReviewCenterPage.tsx`: artifact-backed review event filters, URL query initialization, list/detail, comments, review actions, linked alert display, visual artifact references, and false-negative MVP form.
- `frontend/src/pages/BadCaseCenterPage.tsx`: Stage 8CD artifact-backed Bad Case filters, list/detail, create form, status/root-cause/tag update, and summary cards.
- `frontend/src/pages/EvaluationCenterPage.tsx`: Stage 8EFG artifact-backed Evaluation dataset registry, run trigger, run/result tables, failed case table, and summary view.

Current frontend limitations:

- no zone editor workflow
- no video overlay for trajectories/events/alerts
- no alert timeline
- no complete traffic visualization dashboard or charts
- no complex video overlay editor
- no full review workflow embedded inside Analysis Detail or Alert Center

## Boundaries And Limitations

Current limitations:

- no database-backed Review Center workflow; Stage 7C/7D/7E provide artifact-backed Review API, frontend MVP, and navigation, and Stage 7F audits that as the local Review Center MVP only
- no Evaluation-backed Bad Case regression workflow
- no failed case to Bad Case conversion workflow
- no industrial mAP / IDF1 / MOTA Evaluation metrics
- no database-backed Zone / Rule / Alert persistence
- no video overlay
- no database-backed final Traffic Analysis Center
- no DB-backed result index
- no frontend flow statistics chart
- no frontend congestion chart
- no database-backed flow or zone statistics persistence
- no real-world speed / direction calibration
- no formal traffic enforcement conclusion

Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Alert Center, Review Center, Bad Case Center, and Evaluation Center separate. Review artifacts such as `review_comments.jsonl`, `event_review_state.json`, and `false_negative_events.jsonl` plus the Stage 7C `/api/review` endpoints, Stage 7D/7E frontend, and Stage 7F audit are a local artifact-backed Review MVP; they are not database-backed review state or Evaluation reports. Stage 8CD Bad Case behavior remains artifact-backed through `bad_cases.jsonl`, `bad_case_updates.jsonl`, `/api/bad-cases`, and the React Bad Case Center MVP. Stage 8EFG Evaluation behavior remains artifact-backed through `evals/datasets/evaluation_datasets.json`, `evals/results/*.jsonl`, `evaluation_summary.json`, `/api/evaluation`, `scripts/run_evals.py`, and the React Evaluation Center MVP. It does not imply database final state, failed case conversion, Bad Case regression, or industrial mAP / IDF1 / MOTA completion.
