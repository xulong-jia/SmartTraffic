# API Reference

## Health

- `GET /health`
- `GET /health/ready`
- `GET /api/config`

`GET /health` is a lightweight liveness check. `GET /health/ready` also checks
database connectivity and returns `checks.database=ok` or HTTP `503` with
`checks.database=error`.

## Security / Actor Preview

Full Stage 7CD adds minimal local identity and permission behavior. This is not
production IAM.

Headers:

- `X-SmartTraffic-Actor`
- `X-SmartTraffic-Role`

Roles are `viewer`, `operator`, `reviewer`, and `admin`. Missing headers default
to `actor=system` and `role=operator` for local compatibility.
`SMARTTRAFFIC_AUTH_MODE=permissive` records actor context without blocking
requests. `SMARTTRAFFIC_AUTH_MODE=strict` enforces the preview permission guard:

- `viewer`: read-only.
- `operator`: realtime start / stop, alert actions, and local config writes.
- `reviewer`: review actions and Bad Case actions.
- `admin`: all preview permissions.

Error responses include `error_code`, `message`, `detail`, and `request_id`.
Obvious secret / RTSP / password content is redacted from error messages.

## Videos

- `POST /api/videos/upload`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `GET /api/videos/{video_id}/frames`
- `POST /api/videos/{video_id}/process`
- `GET /api/videos/{video_id}/status`

Full Stage 2AB makes the video API DB-backed for video metadata and processing
task lifecycle state. Full Stage 2CD persists core result rows for successful
processing runs. Upload still stores the source video on local disk, while the
`videos` row stores filename, storage path, status, fps, dimensions, frame
count, duration, camera id, and metadata. `GET /api/videos/{video_id}/frames`
returns rows from the `frames` table; Stage 2CD does not auto-extract frame
images.

`v1.0.3-final-hardening` validates upload extension, size, duration, and codec
before creating the DB video row. Supported extensions remain `.mp4`, `.avi`,
`.mov`, `.mkv`, and `.webm`. Default local limits are
`SMARTTRAFFIC_MAX_UPLOAD_MB=200`,
`SMARTTRAFFIC_MAX_VIDEO_DURATION_SECONDS=600`, and
`SMARTTRAFFIC_ALLOWED_VIDEO_CODECS=avc1,h264,mp4v,xvid,mjpg`. Unsupported
extension, empty upload, unreadable metadata, unsupported codec, or excessive
duration return a clear client error; oversized uploads return `413`. OpenCV
FOURCC / codec detection can vary by platform and container, so unsupported or
undetectable codec errors are validation boundaries rather than production
transcoding guarantees. Error responses do not expose tracebacks or local
absolute paths.

The `frames` API is a frame metadata / query contract for DB-backed local
validation. It is not a guarantee that the processing pipeline persists every
decoded frame image by default.

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
Each process request creates a DB `processing_tasks` row with `pending`,
`running`, `completed`, or `failed` status, progress, start/finish timestamps,
error message, parameters, and result summary. Each successful process request
also creates a `traffic_analysis_runs` row, so one video may have multiple
`run_id` values. Full Stage 2CD imports generated `detections.csv`,
`tracks.csv`, `trajectory_points.csv`, `flow_counts.json`, and
`zone_statistics.json` into DB tables while keeping the artifacts. Full Stage
3AB records the current zone/rule config snapshot in the run summary when the
processing flow creates a DB run. `v1.0.1-audit-polish` also records detector
and tracker business writes in `model_runs` for DB-backed processing flows,
including sanitized detector model path / dry-run parameters, tracker
parameters, summary metrics, and artifact references.

Manual alignment note:

- Stage 5 is implemented as an artifact-based / in-memory MVP.
- Event and alert artifacts remain available for legacy run directories.
- Detection, tracking, trajectory, flow count, and zone statistic reads are
  DB-first with artifact fallback.
- `v1.0.2-spec-alignment` makes
  `GET /api/analysis-runs/{run_id}/alerts` DB-first with artifact fallback,
  matching the rest of the run-scoped Traffic Analysis Center result reads.
- Full Stage 3AB makes Zone / Event Rule CRUD and top-level Event APIs
  DB-backed.
- Full Stage 3CD makes EventEvidence / RuleExecution lifecycle, Alert Center
  status transitions, and Review audit trail DB-first with artifact fallback.
- Full Stage 3EF makes Bad Case / Evaluation workflows DB-first with artifact
  fallback, including failed cases persisted in
  `evaluation_results.summary["failed_cases"]`.

## Zone / Event Rule Config

Full Stage 3AB makes these configuration APIs DB-backed. Responses preserve the
existing shape and include `version`; the DB model stores polygon, direction,
counting-line, target-class, parameter, cooldown, severity, and version data in
the existing structured JSON fields. Full Stage 5AB connects the frontend
ZoneEditor to these APIs so users can draw polygon, direction line, and counting
line geometry, then save and read back DB-backed zones and event rules.
Full Stage 5CD consumes the same zone records in Analysis Detail overlay mode:
polygons, direction lines, counting lines, enabled state, and selected event
zone highlighting are rendered as frontend SVG overlays. Detection, tracking,
trajectory, and event overlays use the existing Analysis Runs read APIs.

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

Event rule severity values are limited to `low`, `medium`, and `high`, matching
the EventEngine contract. `POST /api/event-rules` and
`PATCH /api/event-rules/{rule_id}` enforce this in the backend schema; sending
`critical` as an Event Rule severity is rejected by request validation. Alert
levels are separate generated alert states and may still use `info`, `warning`,
and `critical`.

## Analysis Runs

These endpoints form the Traffic Analysis Center result API surface. Full
Stage 2CD makes the run index and core result reads DB-first while preserving
artifact fallback. Full Stage 3CD adds DB-first Event / Alert / Review lifecycle
reads and writes. Full Stage 3EF adds DB-first Bad Case and Evaluation
workflows while preserving artifact fallback.

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

## Processing Tasks

- `GET /api/processing/tasks`

This endpoint exposes the local processing task registry / DB-backed task
records used by video processing, rule-rerun requests, and realtime preview
start records. Processing task rows include status, mode, progress,
timestamps, error message, parameters, result summary, and related video / run
ids where available. It is DB-backed for Full Stage 2AB+ flows and is used for
local operational visibility, not as a production queue monitor.

`v1.0.1-audit-polish` makes this endpoint DB-first instead of reading only the
legacy in-memory registry. Supported filters are:

- `video_id`
- `run_id`
- `status`
- `mode`
- `task_type` (matches explicit task type values such as `realtime_process` and
  processing modes such as `detection_only`)
- `include_memory` (optional debug compatibility flag, default false, merges
  legacy in-memory tasks after DB rows)

Responses include `id`, `video_id`, `run_id`, `task_type`, `mode`, `status`,
`progress`, `error_message`, `started_at`, `finished_at`, `created_at`,
`params_json`, and `result`.

## Detection / Tracking / Trajectory Resource Placeholders

- `GET /api/detections`
- `GET /api/tracks`
- `GET /api/trajectories`

These are module-boundary placeholder endpoints. Current real result reads are
the run-scoped, DB-first / artifact-fallback Analysis Runs endpoints:

- `GET /api/analysis-runs/{run_id}/detections`
- `GET /api/analysis-runs/{run_id}/tracks`
- `GET /api/analysis-runs/{run_id}/trajectory-points`

The standalone placeholders do not replace the run-scoped result APIs and are
not production aggregate search endpoints.

`tracks` rows in the current local prototype are run-level track records plus
metadata / artifact-compatible rows imported from processing output. They are
not a production normalized per-frame tracking table; detailed per-frame
tracking evidence remains represented through Analysis Runs payloads and local
artifacts where available.

## Reports

Full Stage 6AB/6CD adds a DB-first / artifact-compatible Report Center API for
CSV, JSON, PDF, bundle metadata, keyframe summary, and annotated-video
reference export. It aggregates existing analysis, event, alert, flow, zone,
bad case, and evaluation records. Reports are for analysis and review only;
they are not traffic-enforcement artifacts.

- `GET /api/reports/runs`
- `GET /api/reports/{run_id}/summary`
- `GET /api/reports/{run_id}/bundle`
- `GET /api/reports/{run_id}/export.json`
- `GET /api/reports/{run_id}/export.csv?section=events`
- `GET /api/reports/{run_id}/export.pdf`

Supported CSV `section` values:

- `events`
- `alerts`
- `flow_counts`
- `zone_statistics`
- `bad_cases`
- `evaluation_results`

`GET /api/reports/{run_id}/summary` returns the selected run summary, section
counts, event / alert / bad-case breakdowns, flow totals, evaluation metric
summary, bundle metadata, keyframe summary, annotated video reference,
available export sections, and the non-enforcement note.

`GET /api/reports/{run_id}/export.json` returns a structured JSON report:

```json
{
  "metadata": {
    "schema_version": "full_stage_6ab.report.v1",
    "note": "SmartTraffic reports are for analysis and review only; not for traffic enforcement.",
    "available_exports": ["events", "alerts"]
  },
  "run": {},
  "events": [],
  "alerts": [],
  "flow_counts": [],
  "zone_statistics": [],
  "bad_cases": [],
  "evaluation_results": []
}
```

CSV exports always include a stable header row, even when the selected section
has no rows. Local absolute paths are sanitized before report payloads are
returned.

`GET /api/reports/{run_id}/export.pdf` returns a lightweight text PDF with run
metadata, event / alert / flow / zone / bad case / evaluation summaries,
available artifact references, and explicit non-enforcement disclaimers. The
PDF is generated in memory and is not written to the repository.

`GET /api/reports/{run_id}/bundle` returns metadata only. It lists included
sections, artifact references, keyframe index status, and annotated video
reference status. It does not create a zip, copy large videos, embed keyframe
images, or generate new MP4 artifacts.

Permissions and realtime reporting are intentionally outside Full Stage 6 and
remain for later stages.

### Analysis Runs List

`GET /api/analysis-runs`

This endpoint returns a DB-first run list. It reads `traffic_analysis_runs`
first, then falls back to directories found under `results/traffic_analysis/`
and the in-memory registry for legacy artifact-only runs. Results are
de-duplicated by `run_id`.

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
      "source": "db",
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
- `source` may be `db`, `manifest`, `metadata`, `artifact_index`,
  `in_memory_registry`, or `directory_scan`.
- Invalid JSON in one run's manifest does not make the whole list fail. The
  affected run can fall back to metadata or directory scan and marks that file
  status as `error`.
- Stage 6E frontend Dashboard, Video Center, and Analysis Detail consume this
  response for run counts, recent runs, and artifact status panels.

### Analysis Run Summary

`GET /api/analysis-runs/{run_id}`

This endpoint returns the same Stage 6D summary object used by the list API for
one run. It preserves the legacy `id` field while also exposing `run_id`.

Behavior:

- Missing run returns 404.
- Summary source can be `db`, `manifest`, `metadata`, `artifact_index`,
  `in_memory_registry`, or `directory_scan`.
- DB rows take precedence over artifact fallback when both exist.

### Manifest

`GET /api/analysis-runs/{run_id}/manifest`

This endpoint returns a DB-first run manifest/index representation. For DB runs,
it is built from `traffic_analysis_runs.artifact_index`; for legacy
artifact-only runs, it reads or builds `manifest.json` from the local run
directory and writes `artifact_index.json` when the index is missing.

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
    },
    "keyframes": {
      "status": "available",
      "path": "keyframes/",
      "format": "directory",
      "record_count": 2,
      "required": false
    },
    "keyframes_index": {
      "status": "available",
      "path": "keyframes/index.json",
      "format": "json",
      "record_count": 1,
      "required": false
    },
    "annotated_video": {
      "status": "missing_source_video",
      "path": "annotated_video.mp4",
      "format": "mp4",
      "record_count": 0,
      "required": false
    }
  }
}
```

Artifact status values:

- `available`: file or non-empty directory exists and can be read.
- `missing`: Stage 6B core artifact is expected but not present.
- `planned`: later-stage artifact reserved by contract, such as `evaluation_summary.json`. Older runs without generated Stage 6C statistics may still show `flow_counts.json` or `zone_statistics.json` as planned until those artifacts are generated.
- `empty`: artifact exists and is readable, but has zero records.
- `missing_source_video`: Stage 6F visual artifact generation could not run
  because the source video was not available.
- `error`: artifact status or count could not be read.

Behavior:

- Missing run returns 404.
- Paths are relative to the run directory.
- Stage 6F `keyframes`, `keyframes_index`, and `annotated_video` status are
  exposed through this manifest and through the run summary `artifact_summary`.
- The endpoint does not generate evaluation results.
- Visual artifact generation failures are represented in manifest status and do
  not imply Review / Bad Case / Evaluation behavior.

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
  "track_id": null,
  "source": "db"
}
```

Behavior:

- Missing run returns 404.
- Existing run without trajectory DB rows or trajectory artifacts returns 404.
- `limit=0` returns `summary` with empty `frames` and `rows`.
- `track_id` filters trajectory rows and frame-level `trajectory_points`.

### Events

`GET /api/analysis-runs/{run_id}/events`

This endpoint is a DB-first run event query. When DB event rows exist for the
run, it reads `events`, `event_evidence`, and `rule_executions` and returns
`source=db`. When DB rows are unavailable, it falls back to `events.jsonl`,
`event_evidence.jsonl`, `rule_executions.jsonl`, and `event_summary.json` from a
local run directory.

Full Stage 3AB also provides top-level `/api/events` DB-first APIs. When DB rows
are unavailable and `run_id` is supplied, the top-level list/detail APIs can
fallback to run artifacts.

Top-level Event APIs:

- `GET /api/events?run_id=&video_id=&event_type=&status=&severity=&track_id=`
- `GET /api/events/{event_id}?run_id=`
- `PATCH /api/events/{event_id}/status`
- `POST /api/events/{event_id}/bad-case`

`PATCH /api/events/{event_id}/status` updates the DB event status only. Review
Center actions under `/api/review` write the `review_comments` DB audit trail.
`POST /api/events/{event_id}/bad-case` creates a minimal DB bad-case record
linked to the event, run, video, and track. Full Stage 3EF extends the complete
Bad Case workflow under `/api/bad-cases` with DB-first create/list/detail/update,
filter, summary, from-review, and from-failed-case behavior.

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
  "track_id": null,
  "source": "db"
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

This endpoint returns flow count results DB-first. If DB `flow_counts` rows are
missing but the run artifacts exist, it falls back to the Stage 6C
`flow_counts.json` payload. A run with no `flow_counting` events returns a valid
empty artifact fallback.

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
  "records": [],
  "source": "db"
}
```

Behavior:

- Missing run returns 404.
- Existing run without `flow_counting` events returns an empty artifact.
- Direction values are normalized to `in`, `out`, or `unknown`.
- `source` is `db` for persisted rows and `artifact` for fallback.
- Stage 6E Analysis Detail displays this payload as a minimal summary/table
  view.
- This is not a frontend chart or real-world calibrated
  traffic volume system.

### Zone Statistics

`GET /api/analysis-runs/{run_id}/zone-statistics`

This endpoint returns zone statistics DB-first. If DB `zone_statistics` rows are
missing but the run artifacts exist, it falls back to the Stage 6C
`zone_statistics.json` payload. The artifact builder only aggregates explicit
zone information already present in trajectory points and congestion evidence;
it does not infer new zone membership from geometry at query time.

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
  "congestion_events": [],
  "source": "db"
}
```

Behavior:

- Missing run returns 404.
- Existing run without zone data returns an empty artifact.
- Congestion rule evidence is preserved as `congestion_events`.
- `source` is `db` for persisted rows and `artifact` for fallback.
- Stage 6E Analysis Detail displays this payload as a minimal summary/table
  view.
- This is not a frontend congestion chart or real-world congestion calibration
  system.

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

This endpoint is a DB-first run alert query. When DB `alerts` rows exist for the
run, it reads them by `run_id`, applies the same filters, and returns
`source=db`. When no DB alert rows exist, it falls back to `alerts.jsonl` and
`alert_summary.json` from the local run directory. The standalone Alert Center
endpoints below remain DB-first for DB alert rows and fallback to artifact
alerts for legacy runs.

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
  "event_type": null,
  "source": "db"
}
```

Behavior:

- Missing run returns 404.
- Existing run without DB alert rows and without alert artifacts returns 404.
- `limit=0` returns `summary` with an empty `alerts` list.
- Event rule severity remains `low` / `medium` / `high`; alert `level` remains
  the alert-center concept and may be `info`, `warning`, or `critical`.

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

These endpoints update DB alert rows when a matching DB alert exists. If no DB
alert is found, they fallback to the current artifact-backed MVP storage.

## Review API

Stage 7C implements the artifact-backed Review API MVP. Stage 7D adds a React
Review Center MVP that consumes these endpoints for run filters, event
list/detail, confirm, false-positive, ignore, resolve, comments, and
false-negative creation. Stage 7E adds frontend URL navigation into Review
Center from Analysis Detail and Alert Center. Stage 7F audits this as the
Review Center artifact-backed MVP boundary. Full Stage 3CD adds DB-first Review
workflow behavior for DB events: actions update `events.status`, append
`review_comments` audit rows, and preserve artifact fallback for legacy runs.

Per-run review artifact files used by these APIs:

- `review_comments.jsonl`: append-only audit trail for `confirm`,
  `mark_false_positive`, `add_false_negative`, `ignore`, `resolve`, and
  `comment` actions.
- `event_review_state.json`: derived current review state keyed by `event_id`.
  It does not overwrite the original Event Engine `events.jsonl`.
- `false_negative_events.jsonl`: local MVP records for manually added missed
  events. These records are not Bad Case Center records and are not Evaluation
  ground truth.

Implemented endpoints:

- `GET /api/review/events?run_id=&status=&event_type=&limit=50&offset=0`
- `GET /api/review/events/{event_id}?run_id=`
- `POST /api/review/events/{event_id}/confirm`
- `POST /api/review/events/{event_id}/false-positive`
- `POST /api/review/events/{event_id}/ignore`
- `POST /api/review/events/{event_id}/resolve`
- `POST /api/review/comments`
- `GET /api/review/comments?run_id=&event_id=&limit=50&offset=0`
- `POST /api/review/false-negatives`
- `POST /api/review/events/false-negative`
- `POST /api/review/events/{event_id}/rerun-rule`

`GET /api/review/events` requires `run_id`; this avoids ambiguous global
`event_id` lookup across local artifact directories. Missing event artifacts for
an existing run return an empty list. Missing review artifacts return empty
comments/state. Malformed review artifacts return `400`.

Review event list response shape:

```json
{
  "items": [
    {
      "run_id": "run_xxx",
      "event_id": "event_xxx",
      "event_type": "danger_zone_intrusion",
      "track_id": 17,
      "zone_id": "zone_001",
      "severity": "high",
      "original_status": "pending",
      "review_status": "confirmed",
      "last_action": "confirm",
      "comment_count": 1,
      "linked_alert_ids": ["alert_xxx"],
      "start_frame": 10,
      "end_frame": 12,
      "start_time_ms": 900,
      "end_time_ms": 1000
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

Review action request body:

```json
{
  "run_id": "run_xxx",
  "comment": "confirmed",
  "reviewer": "local_reviewer",
  "alert_id": null
}
```

Action responses include the current review status, the appended review record,
and the current event review state. For DB events, actions update
`events.status` and append `review_comments`. For artifact-only runs, actions
do not overwrite `events.jsonl`.

`POST /api/review/comments` appends a comment-only review record. It preserves
the current status and increments `comment_count`.

`POST /api/review/false-negatives` writes DB false-negative event/review rows
when the run exists in DB, otherwise it writes `false_negative_events.jsonl`,
appends an `add_false_negative` review comment, and updates
`event_review_state.json`. `POST /api/review/events/false-negative` is the DB
workflow endpoint and returns the created `event_id`.

`POST /api/review/events/{event_id}/rerun-rule` records a request as a
`processing_tasks` row with `mode=rule_rerun` and parameters containing
`event_id`, `run_id`, `rule_id`, `requested_by`, and `reason`. It does not run
the rule engine or mutate result artifacts.

False-negative and rerun endpoints do not automatically create Bad Cases and do
not automatically feed Evaluation Center.

Full Stage 5E Review UI uses these endpoints through a ReviewDrawer workflow:
confirm / false-positive / ignore / resolve / comment stay in Review, Review ->
Bad Case calls `POST /api/bad-cases/from-review`, and rule rerun request records
only the `rule_rerun` task described above.

HTTP behavior:

- `400`: missing required `run_id`, invalid state transition, or malformed
  review artifact.
- `404`: run or event not found.
- `422`: request body validation error.

The Stage 7 frontend did not create Bad Case records or feed Evaluation Center,
and Stage 7E navigation does not auto-sync Alert Center status with Event
review status. Stage 8B adds backend artifact/schema/service support for Bad
Case records. Stage 8CD adds routed Bad Case API and a Bad Case Center frontend
MVP. Full Stage 3EF makes Bad Case DB workflow available under
`/api/bad-cases`. Full Stage 5E adds an explicit Review -> Bad Case UI action,
but Review API status actions still do not modify Bad Case records
automatically.

Stage 7E frontend URL query contract:

- `/review?run_id=run_001&event_id=event_123`
- `/review?run_id=run_001&event_id=event_123&alert_id=alert_456`
- `/review?status=pending`
- `/review?run_id=run_001&event_type=wrong_way_driving`

Supported query parameters are `run_id`, `event_id`, `alert_id`, `status`, and
`event_type`. The Review Center initializes filters from these values. With
`run_id + event_id`, it loads the matching event detail. With `alert_id`, it
shows alert context and highlights the linked alert when present. Analysis
Detail only renders a Review link for events; Alert Center only renders a
linked event Review link and keeps acknowledge / resolve / ignore behavior
separate.

## Bad Case API

Stage 8CD implements an artifact-backed Bad Case API MVP. Full Stage 3EF makes
these endpoints DB-first for DB-backed runs while preserving artifact fallback.
DB rows store core fields in `bad_cases` and extended fields such as `video_id`,
`track_id`, `frame_index`, `module`, `root_cause`, `expected_result`,
`actual_result`, `snapshot_path`, `linked_review_id`, and
`linked_failed_case_id` in the JSON payload. Artifact-only runs still read and
write per-run `bad_cases.jsonl`.

Implemented endpoints:

- `GET /api/bad-cases?run_id=&video_id=&event_id=&case_type=&module=&status=&tag=&limit=50&offset=0`
- `GET /api/bad-cases/{case_id}?run_id=`
- `POST /api/bad-cases`
- `PATCH /api/bad-cases/{case_id}`
- `GET /api/bad-cases/summary?run_id=`
- `POST /api/bad-cases/from-review`
- `POST /api/bad-cases/from-failed-case`

`GET /api/bad-cases` supports global discovery across run directories when
`run_id` is omitted. Missing `bad_cases.jsonl` returns an empty list. Malformed
Bad Case artifacts return `400` with a stable error message.

`POST /api/bad-cases/from-review` creates a Bad Case that references
DB `review_comments.id` or `review_comments.jsonl.review_id` through
`linked_review_id`; it does not overwrite Review artifacts or original event
artifacts.

`POST /api/bad-cases/from-failed-case` creates or returns a Bad Case linked to
an Evaluation failed case. It first searches DB
`evaluation_results.summary["failed_cases"]`, then falls back to
`evals/results/failed_cases.jsonl`. It writes `source=evaluation_center` and
`linked_failed_case_id=<failed_case_id>`. The endpoint is idempotent for the
same `run_id` and `failed_case_id`: if a Bad Case already links that failed
case, the existing record is returned. It does not mutate failed case source
records.

HTTP behavior:

- `400`: malformed Bad Case artifact or unsupported business update.
- `404`: analysis run, Bad Case, Review record, or Evaluation failed case not found.
- `422`: request body validation error, including unsupported enum values.

Stage 8HI adds artifact-backed failed case conversion and Bad Case regression
summary MVP. Full Stage 3EF adds DB-backed Bad Case workflow and failed-case
conversion. Full Stage 4CD adds annotation-backed detection / tracking
benchmark rows for tiny fixtures. Full Stage 4E adds deterministic replay /
rule replay regression for Bad Cases. Complete video-level rerun is still not
implemented.

## Evaluation API

Stage 8EFG / Stage 8HI implements an artifact-backed Evaluation API MVP. Full
Stage 3EF adds DB-first Evaluation workflow using `evaluation_datasets` and
`evaluation_results`. Failed cases are persisted inside
`evaluation_results.summary["failed_cases"]`; no separate failed-cases table is
introduced in this stage. Artifacts remain available under
`evals/datasets/evaluation_datasets.json`, `evals/results/`, and per-run
`evaluation_summary.json`.

Available endpoints:

- `GET /api/evaluation/datasets`
- `POST /api/evaluation/datasets`
- `GET /api/evaluation/runs`
- `POST /api/evaluation/run`
- `GET /api/evaluation/results`
- `GET /api/evaluation/summary/{run_id}`
- `GET /api/evaluation/failed-cases`

`POST /api/evaluation/run` accepts `event`, `flow_counting`, `trajectory`,
`detection`, `tracking`, and `regression`. Event / flow / trajectory are MVP
comparisons that can be written to DB. Detection writes `detection_mAP`,
`detection_precision`, `detection_recall`, and `detection_ap_<class>` when
annotation fixtures are available. Tracking writes `tracking_idf1`,
`tracking_mota`, `tracking_id_switches`, and `tracking_track_lost` when
annotation fixtures are available. Without annotations, detection / tracking
return `insufficient_data` with `reason=not_enough_annotations` and do not emit
fake benchmark numbers. Detection mAP is VOC-style single-IoU AP, not COCO
official mAP. Tracking metrics are lightweight deterministic frame-level
association, not TrackEval official implementation. Regression reads Bad Case
DB rows or `bad_cases.jsonl` and uses `config` filters such as `case_type`,
`module`, `status`, `tag`, and `apply_updates`. It writes per-case replay
results plus `regression_pass_rate`, `failed_case_count`, `fixed_case_count`,
and `reopened_case_count`. `apply_updates` defaults to false; when true,
passed open / triaged cases are marked `fixed`, while failed fixed / verified
cases are reopened as `open`. Missing replay payload returns
`insufficient_data` and does not emit a fake pass. This does not execute a
complete video-level rerun pipeline.

Full Stage 5E Evaluation UI presents run / dataset / type filters, result cards,
JSON-friendly result details, failed-case -> Bad Case conversion, regression
summary, and the same non-COCO / non-TrackEval / deterministic replay /
`insufficient_data` boundary labels.

## Cameras API

Full Stage 7AB adds DB-backed camera CRUD for realtime preview configuration.
Supported `source_type` values are `upload`, `rtsp`, `file`, and `mock`.
Normal responses do not return the full `stream_url`; they return
`masked_stream_url` instead. Do not commit real RTSP addresses, local video
paths, secrets, or generated realtime outputs.

Available endpoints:

- `POST /api/cameras`
- `GET /api/cameras?source_type=&enabled=`
- `GET /api/cameras/{camera_id}`
- `PATCH /api/cameras/{camera_id}`
- `DELETE /api/cameras/{camera_id}`
- `POST /api/cameras/{camera_id}/enable`
- `POST /api/cameras/{camera_id}/disable`

Camera response fields include `id`, `name`, `location`, `source_type`,
`masked_stream_url`, `enabled`, `status`, `width`, `height`, `fps`,
`metadata`, `created_at`, and `updated_at`. `stream_url` is accepted on create
and update so the backend can store configuration, but it is not exposed by the
default response models.

HTTP behavior:

- `400`: unsupported source type.
- `404`: camera not found.
- `422`: request body validation error.

## Realtime Preview API

Full Stage 7AB adds a lightweight realtime preview service. It is a metadata
preview, not production realtime monitoring. It does not open real RTSP
connections, does not run Celery or a complex queue, and does not generate video
or frame artifacts. Start creates a DB `processing_tasks` row with
`mode=realtime_process` and a lightweight realtime pseudo-video row so the
existing processing task contract remains linked.

Available endpoints:

- `POST /api/realtime/{camera_id}/start`
- `POST /api/realtime/{camera_id}/stop`
- `GET /api/realtime/{camera_id}/status`
- `GET /api/realtime/{camera_id}/recent-frames`
- `GET /api/realtime/{camera_id}/recent-events`
- `GET /api/realtime/{camera_id}/recent-alerts`

Preview behavior:

- `mock`: generates deterministic recent frame metadata plus one preview event
  and one preview alert.
- `file`: performs local file smoke-level metadata preview and returns only a
  safe source label such as the basename.
- `rtsp`: accepts masked RTSP configuration and returns a no-connect preview
  status without network dependency.
- `upload`: returns upload-preview placeholder metadata.

Recent frames / events / alerts are kept in a bounded in-memory cache
(`max_items=20` per camera). Disabled cameras return `400` on start. Missing
cameras return `404`. Full Stage 7CD adds minimal actor / permission / audit /
readiness hardening around these endpoints. Production IAM, central audit
storage, operations monitoring, and production realtime streaming remain
outside the current local preview.

## Not Implemented From The Manual Yet

The following API capabilities are planned by the execution manual but are not
implemented as working behavior yet:

- advanced filtering on flow counts and zone statistics
- production-grade aggregate statistics APIs
- complete video-level Bad Case rerun pipeline
- COCO official mAP / TrackEval official evaluation
- production realtime monitoring and production IAM
- Full final `v1.0.0` release tag; Stage 8AB only prepares final audit docs

## Placeholders For Later Phases

Stage 8EFG / Stage 8HI Evaluation APIs are routed under `/api/evaluation` and
documented above.

These placeholder endpoints exist to preserve module boundaries. Standalone
event and alert center APIs remain separate from the artifact-based
`analysis-runs` list, summary, event, statistics, and alert endpoints
documented above. Review API MVP is available under `/api/review`, the Stage 7
Review Center frontend consumes it, and Stage 7F confirms the artifact-backed
Review Center MVP boundary. Stage 8CD adds artifact-compatible Bad Case APIs
and frontend workflow. Stage 8EFG adds Evaluation APIs and frontend workflow.
Stage 8HI adds failed case conversion and Bad Case regression summary MVP. Full
Stage 3EF makes Bad Case and Evaluation DB-first with artifact fallback.
Complete video-level rerun, COCO official metrics, TrackEval official metrics,
and production hardening remain outside the current implementation.
