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
after trajectory artifacts are written, writes Stage 6C traffic statistics
artifacts after event artifacts, then runs AlertService. If `event_rules` /
`zones` are omitted, the process still writes stable empty event, statistics,
and alert artifacts. The process response keeps the existing summary shape; full
event, statistics, and alert details are queried from analysis-runs endpoints.

Manual alignment note:

- Stage 5 is implemented as an artifact-based / in-memory MVP.
- Event, traffic statistics, and alert endpoints documented below are
  artifact-based MVP endpoints.
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
- `GET /api/analysis-runs/{run_id}/manifest`
- `GET /api/analysis-runs/{run_id}/detections?limit=100`
- `GET /api/analysis-runs/{run_id}/tracks?limit=100`
- `GET /api/analysis-runs/{run_id}/trajectory-points?limit=100`
- `GET /api/analysis-runs/{run_id}/events?limit=100`
- `GET /api/analysis-runs/{run_id}/flow-counts`
- `GET /api/analysis-runs/{run_id}/zone-statistics`
- `POST /api/analysis-runs/{run_id}/alerts/generate`
- `GET /api/analysis-runs/{run_id}/alerts?limit=100`
- `GET /api/alerts`
- `GET /api/alerts/{alert_id}`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/{alert_id}/resolve`
- `PATCH /api/alerts/{alert_id}/ignore`

### Analysis Runs List

`GET /api/analysis-runs`

This Stage 6D endpoint returns an artifact-backed run list. It combines the
in-memory processing registry with directories found under
`results/traffic_analysis/`, de-duplicates by `run_id`, and builds summaries
from the best available source in this order: `manifest.json`, `metadata.json`,
`artifact_index.json`, in-memory registry, then directory scan fallback. It does
not use a database.

Query parameters:

- `status`: optional run status filter.
- `video_id`: optional video id filter.
- `limit`: integer from 0 to 1000, default 50.
- `offset`: integer greater than or equal to 0, default 0.

Response shape:

```json
{
  "items": [
    {
      "schema_version": "stage6d.v1",
      "id": "run_xxx",
      "run_id": "run_xxx",
      "video_id": "video_xxx",
      "status": "completed",
      "mode": "offline",
      "result_dir": "results/traffic_analysis/run_xxx",
      "source": "manifest",
      "metadata": {
        "available": true,
        "path": "metadata.json",
        "status": "available"
      },
      "manifest": {
        "available": true,
        "path": "manifest.json",
        "status": "available",
        "schema_version": "stage6b.v1"
      },
      "artifact_index": {
        "available": true,
        "path": "artifact_index.json",
        "status": "available"
      },
      "artifact_summary": {
        "detections_csv": {
          "status": "available",
          "path": "detections.csv",
          "record_count": 123
        }
      }
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

Behavior:

- Results are sorted by `updated_at`, `finished_at`, or `created_at`
  descending, with `run_id` as a stable fallback.
- Paths are relative or sanitized for frontend use; local absolute paths are
  not exposed.
- Invalid JSON in one run's manifest does not make the whole list fail. The
  affected run can fall back to metadata or directory scan and marks that file
  status as `error`.

### Analysis Run Summary

`GET /api/analysis-runs/{run_id}`

This endpoint returns the same Stage 6D summary object used by the list API for
one run. It preserves the legacy `id` field while also exposing `run_id`.

Behavior:

- Missing run returns 404.
- Summary source can be `manifest`, `metadata`, `artifact_index`,
  `in_memory_registry`, or `directory_scan`.
- This endpoint is an artifact-based result index, not a DB-backed result
  index.

### Manifest

`GET /api/analysis-runs/{run_id}/manifest`

This endpoint returns the Stage 6B/6C run artifact manifest. It reads or builds
`manifest.json` from the local run directory and writes `artifact_index.json`
when the index is missing. It is artifact-backed and does not use a database.

Response shape:

```json
{
  "schema_version": "stage6b.v1",
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "status": "completed",
  "created_at": "2026-01-01T00:00:00+00:00",
  "updated_at": "2026-01-01T00:00:00+00:00",
  "result_dir": "results/traffic_analysis/run_xxx",
  "artifacts": {
    "metadata": {
      "status": "available",
      "path": "metadata.json",
      "format": "json",
      "record_count": 1,
      "required": true
    },
    "flow_counts": {
      "status": "available",
      "path": "flow_counts.json",
      "format": "json",
      "record_count": 8,
      "required": false
    }
  }
}
```

Artifact status values:

- `available`: file or non-empty directory exists and can be read.
- `missing`: Stage 6B core artifact is expected but not present.
- `planned`: later-stage artifact reserved by contract, such as `evaluation_summary.json`, `annotated_video.mp4`, or `keyframes/`. Older runs without generated Stage 6C statistics may still show `flow_counts.json` or `zone_statistics.json` as planned until those artifacts are generated.
- `empty`: artifact exists and is readable, but has zero records.
- `error`: artifact status or count could not be read.

Behavior:

- Missing run returns 404.
- Paths are relative to the run directory.
- The endpoint does not generate keyframes, annotated video, evaluation results, or database rows.

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

### Flow Counts

`GET /api/analysis-runs/{run_id}/flow-counts`

This endpoint returns the Stage 6C artifact-backed `flow_counts.json` payload.
If the run exists but the statistics file is missing, the service builds it
from local `events.jsonl` and `event_evidence.jsonl` artifacts. A run with no
`flow_counting` events returns a valid empty artifact.

Response shape:

```json
{
  "schema_version": "stage6.flow_counts.v1",
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "window_ms": 60000,
  "source_artifacts": {
    "events": "events.jsonl",
    "event_evidence": "event_evidence.jsonl",
    "rule_executions": "rule_executions.jsonl"
  },
  "summary": {
    "total_count": 0,
    "vehicle_count": 0,
    "person_count": 0,
    "by_class": {},
    "by_zone": {},
    "by_line": {},
    "by_direction": {}
  },
  "windows": [],
  "records": []
}
```

Behavior:

- Missing run returns 404.
- Existing run without `flow_counting` events returns an empty artifact.
- Direction values are normalized to `in`, `out`, or `unknown`.
- This is not a frontend chart, database aggregate, or real-world calibrated
  traffic volume system.

### Zone Statistics

`GET /api/analysis-runs/{run_id}/zone-statistics`

This endpoint returns the Stage 6C artifact-backed `zone_statistics.json`
payload. If the run exists but the statistics file is missing, the service
builds it from local `trajectory_points.jsonl`, `events.jsonl`, and
`event_evidence.jsonl` artifacts. It only aggregates explicit zone information
already present in trajectory points and congestion evidence; it does not infer
new zone membership from geometry at query time.

Response shape:

```json
{
  "schema_version": "stage6.zone_statistics.v1",
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "window_ms": 60000,
  "source_artifacts": {
    "trajectory_points": "trajectory_points.jsonl",
    "events": "events.jsonl",
    "event_evidence": "event_evidence.jsonl"
  },
  "summary": {
    "zone_count": 0,
    "total_windows": 0,
    "vehicle_count": 0,
    "person_count": 0,
    "max_vehicle_count": 0,
    "min_avg_speed_px_per_frame": null,
    "congestion_event_count": 0
  },
  "windows": [],
  "congestion_events": []
}
```

Behavior:

- Missing run returns 404.
- Existing run without zone data returns an empty artifact.
- Congestion rule evidence is preserved as `congestion_events`.
- This is not a frontend congestion chart, database persistence layer, or
  real-world congestion calibration system.

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
- advanced filtering on flow counts and zone statistics
- database-backed aggregate statistics APIs
- full Review / Bad Case / Evaluation APIs

## Placeholders For Later Phases

- `GET /api/detections`
- `GET /api/tracks`
- `GET /api/zones`
- `GET /api/review/events`
- `GET /api/bad-cases`
- `GET /api/evaluation/results`

These placeholder endpoints exist to preserve module boundaries. Standalone event and alert center APIs remain separate from the artifact-based `analysis-runs` list, summary, event, statistics, and alert endpoints documented above. Review, bad-case, and evaluation behavior belongs to later phases and is not implemented as completed logic.
