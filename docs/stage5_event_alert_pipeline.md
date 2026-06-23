# Stage 5 Event & Alert MVP Status

## 1. Scope

This document records the current Stage 5 artifact-based / in-memory MVP state
for SmartTraffic.

The current milestone is the Event & Alert artifact pipeline:

```text
trajectory artifacts
  -> EventService / EventEngine
  -> event artifacts
  -> AlertService
  -> alert artifacts
  -> FastAPI query and alert status endpoints
  -> React Analysis Detail / Alert Center minimal views
```

The current system does not provide law-enforcement-grade violation judgment and does not perform real-world speed calibration.

## 2. Implemented MVP Capabilities

Implemented Stage 5 MVP capabilities:

- Event contract
- Event evidence contract
- Rule execution contract
- Zone / Event Rule configuration API MVP
- Event artifacts
- Event Evidence and Rule Execution artifact enrichment
- EventEngine callback framework
- Six rule callbacks
- EventService
- Process pipeline integration after `mode=detection_tracking_trajectory`
- Artifact-based event query API
- Alert contract
- AlertService
- Artifact-based alert generate/query/status API
- Frontend minimal event and alert views

Current services operate on local artifacts under `results/traffic_analysis/<run_id>/`. They do not form a complete database-backed result center.

## 3. Strict Manual Alignment

The Stage 5 event rule layer covers the six manual-defined event rules. The
process pipeline runs EventEngine / EventService and AlertService after
trajectory processing. Zone / Event Rule config and Alert Center are MVP
implementations, not database-backed final implementations.

The current `v0.5.0-event-alert-minimal` tag is a minimal milestone tag. It is
not a full Stage 5 completion tag and should not be moved.

## 4. Event Rules

### danger_zone_intrusion

Purpose: detect a tracked vehicle or person inside a `danger_zone`.

Inputs:

- trajectory point `center`, `bottom_center`, or `bbox`
- `track_id`
- `class_name`
- `frame_index`
- `timestamp_ms`
- `zone_id`
- zone polygon with `zone_type=danger_zone`

Output:

- `event_type=danger_zone_intrusion`
- event evidence with zone and point details
- matched / skipped / error rule execution records

Limitations:

- no video overlay
- no keyframe snapshot generation
- no law-enforcement conclusion

### pedestrian_in_vehicle_lane

Purpose: detect a `person` inside a `vehicle_lane` polygon.

Inputs:

- trajectory point `center`, `bottom_center`, or `bbox`
- `class_name=person`
- `track_id`
- `frame_index`
- `timestamp_ms`
- zone polygon with `zone_type=vehicle_lane`

Output:

- `event_type=pedestrian_in_vehicle_lane`
- event evidence with vehicle-lane zone and point details
- rule execution records

Limitations:

- no Review Center flow
- no video overlay
- no automated safety action

### illegal_parking

Purpose: detect a vehicle stopped in a configured no-parking or vehicle-lane zone based on pixel-level trajectory features.

Inputs:

- vehicle `class_name`
- `speed_px_per_frame`
- `speed_px_per_second`
- `dwell_time_ms`
- `track_length`
- zone polygon with supported zone type

Output:

- `event_type=illegal_parking`
- dwell/zone evidence
- rule execution records

Limitations:

- pixel-level speed and dwell only
- no real-world speed calibration
- no formal parking violation conclusion
- no law-enforcement-grade judgment

### wrong_way_driving

Purpose: detect vehicles moving in a clear opposite direction inside a configured `vehicle_lane` zone.

Inputs:

- vehicle class: `car`, `truck`, `bus`, or `motorcycle`
- `zone_id`
- `vehicle_lane` polygon
- `point_type`: `bottom_center` or `center`
- `moving_angle`
- `allowed_angle`
- `angle_tolerance`
- `min_speed_px_per_frame`
- `track_length`

Angle convention:

- 0 degrees: right
- 90 degrees: down
- 180 degrees: left
- 270 degrees: up

Strict wrong-way logic:

```text
angle_diff = angle_difference(moving_angle, allowed_angle)
wrong_way = angle_diff >= 180 - angle_tolerance
```

This rule does not use `angle_diff > angle_tolerance`; that looser check means "not following the allowed direction" and can misclassify lateral motion. Lateral motion is not treated as `wrong_way_driving`.

Output:

- `event_type=wrong_way_driving`
- `evidence_type=direction`
- matched / skipped / error rule execution records

Evidence fields:

- `zone_id`
- `zone_type`
- `point`
- `point_type`
- `moving_angle`
- `allowed_angle`
- `angle_tolerance`
- `angle_difference`
- `speed_px_per_frame`
- `min_speed_px_per_frame`
- `direction_vector`
- `track_length`
- `polygon`

Limitations:

- no real-world direction calibration
- no multi-frame wrong-way counter yet
- `min_wrong_way_frames > 1` is currently unsupported
- not law-enforcement-grade judgement

### flow_counting

Purpose: count vehicle or person track crossings over a configured counting line
as Stage 5 event records.

Inputs:

- `line_id`
- `line` from `rule.parameters.line`, formatted as `[[x1, y1], [x2, y2]]`
- `direction`: `any`, `positive`, or `negative`
- `point_type`: `bottom_center` or `center`
- `count_once_per_track`
- `track_id`
- `class_name`
- `frame_index`
- `timestamp_ms`

Runtime behavior:

- compares the current point with the callback state's previous point for the
  same rule / track / point type
- checks whether that segment crosses the configured counting line
- filters crossing direction when `direction` is `positive` or `negative`
- tracks counted keys when `count_once_per_track` is enabled, defaulting to true
- clears previous point and counted-key state when `EventEngine.reset()` runs

Output:

- `event_type=flow_counting`
- `evidence_type=line_crossing`
- matched / skipped / error rule execution records

Evidence fields:

- `line_id`
- `line`
- `previous_point`
- `current_point`
- `point_type`
- `crossing_direction`
- `configured_direction`
- `count_once_per_track`
- `track_id`
- `class_name`
- `frame_index`
- `timestamp_ms`

Limitations:

- no `flow_counts.json`
- no `/api/analysis-runs/{run_id}/flow-counts` API
- no aggregate in/out counts
- no count-per-minute output
- no frontend statistics chart
- no persistent counting line config
- no real-world flow calibration

### congestion

Purpose: detect low-speed, high-density vehicle states inside a configured zone
as Stage 5 event records.

Inputs:

- `rule_mode=aggregate`
- `zone_id`
- `zone_types`: typically `vehicle_lane` or `roi`
- `point_type`: `bottom_center` or `center`
- `vehicle_count_threshold`
- `avg_speed_threshold`
- `min_congestion_frames`
- frame-level `trajectory_points`

Runtime behavior:

- runs as a Stage 5 aggregate event rule
- EventEngine calls each aggregate rule once per frame
- callback reads the full `frame_result["trajectory_points"]`
- filters vehicle classes and track length inside the callback
- counts zone-contained vehicles and computes `avg_speed_px_per_frame`
- EventEngine state tracks consecutive congestion frames
- aggregate EventEngine cooldown / dedup handles repeated zone-level events

Output:

- `event_type=congestion`
- `evidence_type=zone_statistics`
- `track_id=None`
- matched / skipped / error rule execution records

Evidence fields:

- `zone_id`
- `zone_type`
- `frame_index`
- `timestamp_ms`
- `vehicle_count`
- `vehicle_count_threshold`
- `avg_speed_px_per_frame`
- `avg_speed_threshold`
- `track_ids`
- `class_counts`
- `min_congestion_frames`
- `congestion_frame_count`
- `polygon`

Limitations:

- no `zone_statistics.json`
- no `/api/analysis-runs/{run_id}/zone-statistics` API
- no aggregate zone statistics history
- no frontend congestion chart
- no database-backed zone statistics persistence
- no real-world congestion calibration

## 5. Event Artifacts

EventService and TrafficArtifactWriter can generate:

```text
results/traffic_analysis/<run_id>/
  events.jsonl
  event_evidence.jsonl
  rule_executions.jsonl
  event_summary.json
```

`events.jsonl` contains generated event objects.

`event_evidence.jsonl` contains event-linked evidence records.

`rule_executions.jsonl` records matched, skipped, error, and optional not-matched rule execution results.

`event_summary.json` contains event counts by type, severity, status, unique tracks, rule execution counts, and first/last event time.

## 6. Event API

`GET /api/analysis-runs/{run_id}/events`

This is an artifact-based MVP run event query endpoint. It is not the final
standalone Event Center API from the execution manual.

Query parameters:

- `limit`: 0-1000, default 100
- `event_type`: optional
- `track_id`: optional

Response includes:

- `summary`
- `events`
- `event_evidence`
- `rule_executions`

Missing run or missing event artifacts return 404.

## 7. Alert Pipeline

The minimal alert pipeline converts event artifacts into alert artifacts:

```text
events.jsonl
  -> AlertService
  -> alerts.jsonl
  -> alert_summary.json
```

Severity to alert level mapping:

| Event severity | Alert level |
| --- | --- |
| low | info |
| medium | warning |
| high | critical |

Generated alerts default to:

```text
status = new
```

The artifact-backed Alert Center API can query generated alerts and update their
status to acknowledged, resolved, or ignored. It does not implement notification
delivery, real-time alerting, or database-backed alert persistence.

## 8. Alert API

`POST /api/analysis-runs/{run_id}/alerts/generate`

Generates:

- `alerts.jsonl`
- `alert_summary.json`

It reads existing event artifacts and does not modify event artifacts.

`GET /api/analysis-runs/{run_id}/alerts`

These are run-scoped artifact-based alert endpoints.

Query parameters:

- `limit`: 0-1000, default 100
- `status`: optional
- `level`: optional
- `event_type`: optional

Missing run or missing alert artifacts return 404.

`GET /api/alerts`

Lists alerts across available run artifacts.

Query parameters:

- `run_id`: optional
- `status`: optional
- `level`: optional

`GET /api/alerts/{alert_id}`

Returns one alert by `id` / `alert_id`.

`PATCH /api/alerts/{alert_id}/acknowledge`

Marks an alert as acknowledged. The request body may include
`acknowledged_by`.

`PATCH /api/alerts/{alert_id}/resolve`

Marks an alert as resolved.

`PATCH /api/alerts/{alert_id}/ignore`

Marks an alert as ignored.

The standalone Alert Center endpoints remain artifact-backed MVP endpoints, not
database-backed final lifecycle persistence.

## 9. Frontend Minimal View

`AnalysisDetailPage` currently provides:

- trajectory summary / rows / frames
- event summary
- events table
- event evidence table
- rule executions table
- alert generation button
- alert summary
- alerts table

`AlertCenterPage` currently provides:

- run, status, and level filters
- alert list cards
- alert details including run, event, track, and zone identifiers
- acknowledge, resolve, and ignore actions
- loading, error, and empty states

Current frontend does not provide:

- event timeline
- alert timeline
- video overlay
- Review Center workflow

## 10. Tests

Current Stage 5 MVP test coverage includes:

- alert contract tests
- alert service tests
- alert API tests
- stage5 event pipeline tests
- event contract tests
- event evidence tests
- rule execution contract tests
- event artifact writer tests
- event engine tests
- event service tests
- event API tests
- rule callback tests for:
  - `danger_zone_intrusion`
  - `pedestrian_in_vehicle_lane`
  - `illegal_parking`
  - `wrong_way_driving`
  - `flow_counting`
  - `congestion`

The full backend test suite has passed for this milestone, and frontend `npm run build` has passed.

## 11. Known Limitations

Current known limitations:

- `flow_counts.json` is not generated
- `/api/analysis-runs/{run_id}/flow-counts` is not implemented
- aggregate flow statistics and frontend flow charts are not implemented
- `zone_statistics.json` is not generated
- `/api/analysis-runs/{run_id}/zone-statistics` is not implemented
- aggregate zone statistics history and frontend congestion charts are not implemented
- Review Center is not implemented
- Bad Case Center is not implemented
- Evaluation Center is not implemented
- database-backed Zone / Rule / Alert persistence is not implemented
- video overlay is not implemented
- no real-world speed / direction calibration
- no law-enforcement-grade traffic violation judgment

## 12. Next Steps

Recommended next steps:

- Decide whether to add database-backed rule/zone/alert persistence.
- Keep `v0.5.0-event-alert-minimal` as the existing minimal milestone tag; do not move it.
