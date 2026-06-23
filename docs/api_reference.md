# API Reference

## Health

- `GET /health`
- `GET /api/config`

## Videos

- `POST /api/videos/upload`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `POST /api/videos/{video_id}/process`
- `GET /api/videos/{video_id}/status`

`POST /api/videos/{video_id}/process` supports:

- `mode=detection_only`
- `mode=detection_tracking`
- `mode=detection_tracking_trajectory`
- `detector_dry_run`
- `tracker_dry_run`
- `frame_stride`
- `max_frames`
- `conf_threshold`
- `iou_threshold`
- `write_preview`
- `direction_window`
- `dwell_speed_threshold`
- `max_history_points`
- `event_rules`: optional list of EventEngine rule dictionaries.
- `zones`: optional list of zone dictionaries.
- `run_events`: optional boolean, default true.
- `generate_alerts`: optional boolean, default true.
- `record_not_matched`: optional boolean, default false.

Stage four trajectory request example:

```json
{
  "mode": "detection_tracking_trajectory",
  "detector_dry_run": true,
  "tracker_dry_run": true,
  "frame_stride": 1,
  "max_frames": 5,
  "direction_window": 2,
  "dwell_speed_threshold": 1.0,
  "max_history_points": null,
  "event_rules": [],
  "zones": [],
  "run_events": true,
  "generate_alerts": true
}
```

Stage four response fields include:

- `stage = stage_4_trajectory_engine`
- `next_stage = stage_5_event_engine_not_started`
- `total_trajectory_points`
- `trajectory_track_state_counts`
- `avg_track_length`
- `max_track_length`
- `avg_speed_px_per_second`

`avg_speed_px_per_second` is a pixel-level speed estimate derived from timestamp or fps. It is not real-world speed in m/s or km/h.

For `mode=detection_tracking_trajectory`, the process API now runs EventService
after trajectory artifacts are written, then runs AlertService after event
artifacts are written. If `event_rules` / `zones` are omitted, the process still
writes stable empty event and alert artifacts. The process response keeps the
existing summary shape; full event and alert details are queried from
analysis-runs endpoints.

Manual alignment note:

- Stage 5 is implemented as an artifact-based / in-memory MVP.
- Event and alert endpoints documented below are artifact-based MVP endpoints.
- They are not a database-backed final Traffic Analysis Center implementation.

## Zone / Event Rule Config

These endpoints are Stage 5A artifact-based / in-memory MVP configuration APIs.
They provide stable Event Engine input without claiming database persistence.

Zones:

- `POST /api/zones`
- `GET /api/zones?video_id=&enabled=`
- `GET /api/zones/{zone_id}`
- `PATCH /api/zones/{zone_id}`
- `DELETE /api/zones/{zone_id}`

Event Rules:

- `POST /api/event-rules`
- `GET /api/event-rules?event_type=&enabled=&zone_id=`
- `GET /api/event-rules/{rule_id}`
- `PATCH /api/event-rules/{rule_id}`
- `DELETE /api/event-rules/{rule_id}`

Supported `event_type` values:

- `wrong_way_driving`
- `illegal_parking`
- `danger_zone_intrusion`
- `pedestrian_in_vehicle_lane`
- `congestion`
- `flow_counting`

## Analysis Runs

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/detections?limit=100`
- `GET /api/analysis-runs/{run_id}/tracks?limit=100`
- `GET /api/analysis-runs/{run_id}/trajectory-points?limit=100`
- `GET /api/analysis-runs/{run_id}/events?limit=100`
- `POST /api/analysis-runs/{run_id}/alerts/generate`
- `GET /api/analysis-runs/{run_id}/alerts?limit=100`
- `GET /api/alerts`
- `GET /api/alerts/{alert_id}`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/{alert_id}/resolve`
- `PATCH /api/alerts/{alert_id}/ignore`

### Trajectory Points

`GET /api/analysis-runs/{run_id}/trajectory-points`

Query parameters:

- `limit`: integer from 0 to 1000, default 100.
- `track_id`: optional integer. When set, rows and each frame's `trajectory_points` are filtered to that track.

Response shape:

```json
{
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "summary": {},
  "frames": [],
  "rows": [],
  "limit": 100,
  "track_id": null
}
```

Behavior:

- Missing run returns 404.
- Existing run without trajectory artifacts returns 404.
- `limit=0` returns `summary` with empty `frames` and `rows`.
- `track_id` filters trajectory rows and frame-level `trajectory_points`.

### Events

`GET /api/analysis-runs/{run_id}/events`

This endpoint is an artifact-based run event query. It reads `events.jsonl`,
`event_evidence.jsonl`, `rule_executions.jsonl`, and `event_summary.json` from a
local run directory. It is not the execution manual's final standalone
`/api/events` Event Center implementation.

Query parameters:

- `limit`: integer from 0 to 1000, default 100.
- `event_type`: optional string. Filters returned events by event type, such as `danger_zone_intrusion`, `pedestrian_in_vehicle_lane`, `illegal_parking`, `wrong_way_driving`, `flow_counting`, or `congestion`.
- `track_id`: optional integer. Filters returned events, event evidence, and rule executions by track.

Response shape:

```json
{
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "summary": {},
  "events": [],
  "event_evidence": [],
  "rule_executions": [],
  "limit": 100,
  "event_type": null,
  "track_id": null
}
```

Behavior:

- Missing run returns 404.
- Existing run without event artifacts returns 404.
- `limit=0` returns `summary` with empty `events`, `event_evidence`, and `rule_executions`.
- The response does not expose local absolute paths.
- Current implemented rule callbacks are `danger_zone_intrusion`, `pedestrian_in_vehicle_lane`, `illegal_parking`, `wrong_way_driving`, `flow_counting`, and `congestion`.

### Alert Generation

`POST /api/analysis-runs/{run_id}/alerts/generate`

This endpoint reads existing `events.jsonl` and generates:

- `alerts.jsonl`
- `alert_summary.json`

It does not modify event artifacts. Alert status changes are handled by the
standalone `/api/alerts/{alert_id}/...` endpoints below.

Response shape:

```json
{
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "status": "completed",
  "total_alerts": 0,
  "alert_summary": {},
  "artifacts": {}
}
```

Behavior:

- Missing run returns 404.
- Existing run without event artifacts returns 404.
- Alerts are generated from existing event artifacts, not from model inference.

### Alerts

`GET /api/analysis-runs/{run_id}/alerts`

This endpoint is an artifact-based run alert query. The standalone Alert Center
MVP endpoints are listed below.

Query parameters:

- `limit`: integer from 0 to 1000, default 100.
- `status`: optional string. Currently generated alerts default to `new`.
- `level`: optional string. Supported generated levels are `info`, `warning`, and `critical`.
- `event_type`: optional string. Filters alerts by source event type.

Response shape:

```json
{
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "summary": {},
  "alerts": [],
  "limit": 100,
  "status": null,
  "level": null,
  "event_type": null
}
```

Behavior:

- Missing run returns 404.
- Existing run without alert artifacts returns 404.
- `limit=0` returns `summary` with an empty `alerts` list.
### Alert Center

`GET /api/alerts`

Query parameters:

- `run_id`: optional run id filter.
- `status`: optional alert status filter: `new`, `acknowledged`, `resolved`, or `ignored`.
- `level`: optional alert level filter: `info`, `warning`, or `critical`.

Response shape:

```json
{
  "alerts": [],
  "total": 0,
  "run_id": null,
  "status": null,
  "level": null
}
```

`GET /api/alerts/{alert_id}` returns one alert or 404.

`PATCH /api/alerts/{alert_id}/acknowledge`

Optional body:

```json
{
  "acknowledged_by": "operator_1"
}
```

Sets `status=acknowledged`, writes `acknowledged_by`, and writes
`acknowledged_at`.

`PATCH /api/alerts/{alert_id}/resolve` sets `status=resolved` and writes
`resolved_at`.

`PATCH /api/alerts/{alert_id}/ignore` sets `status=ignored`.

These endpoints update the current artifact-backed MVP storage. They are not a
database-backed workflow engine.

## Not Implemented From The Manual Yet

The following API capabilities are planned by the execution manual but are not
implemented as working behavior yet:

- `PATCH /api/events/{event_id}/status`
- standalone `/api/events` full query
- `/api/analysis-runs/{run_id}/flow-counts`
- `/api/analysis-runs/{run_id}/zone-statistics`
- `zone_statistics.json` generation and aggregate zone statistics APIs
- full Review / Bad Case / Evaluation APIs

## Placeholders For Later Phases

- `GET /api/detections`
- `GET /api/tracks`
- `GET /api/zones`
- `GET /api/review/events`
- `GET /api/bad-cases`
- `GET /api/evaluation/results`

These placeholder endpoints exist to preserve module boundaries. Standalone event and alert center APIs remain separate from the artifact-based `analysis-runs` event and alert endpoints documented above. Review, bad-case, and evaluation behavior belongs to later phases and is not implemented as completed logic.
