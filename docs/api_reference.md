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

These endpoints form the Stage 6 Traffic Analysis Center artifact-based MVP
API surface. They read local run artifacts and manifest status; they do not
implement a database-backed final result center, Review Center, Bad Case
Center, or Evaluation Center.

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
- Stage 6E frontend Dashboard, Video Center, and Analysis Detail consume this
  response for run counts, recent runs, and artifact status panels.

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

This endpoint returns the Stage 6B/6C/6F run artifact manifest. It reads or
builds `manifest.json` from the local run directory and writes
`artifact_index.json` when the index is missing. It is artifact-backed and does
not use a database.

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
- The endpoint does not generate evaluation results or database rows.
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

The standalone `GET /api/events` route currently remains contract-only /
placeholder. Real event reads in the Stage 7 MVP should use this
`/api/analysis-runs/{run_id}/events` endpoint for run artifacts, or the Review
API under `/api/review` for review-oriented event list/detail behavior.

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
- Stage 6E Analysis Detail displays this payload as a minimal summary/table
  view.
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
- Stage 6E Analysis Detail displays this payload as a minimal summary/table
  view.
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

## Review API

Stage 7C implements the artifact-backed Review API MVP. Stage 7D adds a React
Review Center MVP that consumes these endpoints for run filters, event
list/detail, confirm, false-positive, ignore, resolve, comments, and
false-negative creation. Stage 7E adds frontend URL navigation into Review
Center from Analysis Detail and Alert Center. Stage 7F audits this as the
Review Center artifact-backed MVP boundary. The API reads Stage 6 event, alert,
and visual artifacts, then writes Stage 7B review artifacts. It is not a
database-backed final review workflow.

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
and the current event review state. Review actions do not overwrite
`events.jsonl`.

`POST /api/review/comments` appends a comment-only review record. It preserves
the current status and increments `comment_count`.

`POST /api/review/false-negatives` writes `false_negative_events.jsonl`, appends
an `add_false_negative` review comment, and updates `event_review_state.json`.
It does not create a Bad Case and does not feed Evaluation Center.

HTTP behavior:

- `400`: missing required `run_id`, invalid state transition, or malformed
  review artifact.
- `404`: run or event not found.
- `422`: request body validation error.

The Stage 7 frontend does not create Bad Case records, does not feed
Evaluation Center, and Stage 7E navigation does not auto-sync Alert Center
status with Event review status. Stage 8B adds backend artifact/schema/service
support for Bad Case records. Stage 8CD adds routed Bad Case API and a Bad
Case Center frontend MVP. Review artifacts can be referenced by Bad Cases, but
Review API actions still do not modify Bad Case records automatically.

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

Stage 8CD implements an artifact-backed Bad Case API MVP. It reads and writes
per-run `bad_cases.jsonl`, records auditable updates in `bad_case_updates.jsonl`,
and refreshes manifest / metadata / artifact index summaries through the Stage
8B artifact helper. It is not database-backed final Bad Case state.

Implemented endpoints:

- `GET /api/bad-cases?run_id=&case_type=&module=&status=&tag=&limit=50&offset=0`
- `GET /api/bad-cases/{case_id}?run_id=`
- `POST /api/bad-cases`
- `PATCH /api/bad-cases/{case_id}`
- `GET /api/bad-cases/summary?run_id=`
- `POST /api/bad-cases/from-review`

`GET /api/bad-cases` supports global discovery across run directories when
`run_id` is omitted. Missing `bad_cases.jsonl` returns an empty list. Malformed
Bad Case artifacts return `400` with a stable error message.

`POST /api/bad-cases/from-review` creates a Bad Case that references
`review_comments.jsonl.review_id` through `linked_review_id`; it does not
overwrite `review_comments.jsonl`, `event_review_state.json`,
`false_negative_events.jsonl`, or `events.jsonl`.

HTTP behavior:

- `400`: malformed Bad Case artifact or unsupported business update.
- `404`: analysis run, Bad Case, or Review record not found.
- `422`: request body validation error, including unsupported enum values.

Stage 8EFG adds artifact-backed Evaluation APIs and MVP metrics. Failed case
conversion, Bad Case regression, industrial mAP / IDF1 / MOTA, and
database-backed Bad Case / Evaluation state are still not implemented.

## Evaluation API

Stage 8EFG implements an artifact-backed Evaluation API MVP. It stores
dataset registry data under `evals/datasets/evaluation_datasets.json`, run and
result indexes under `evals/results/`, and writes per-run
`evaluation_summary.json` into the analysis run directory.

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
artifact comparisons. Detection and tracking return `not_applicable` unless
future annotation-backed metrics are added. Regression returns `planned`; it
does not execute Stage 8H Bad Case regression or convert failed cases into Bad
Cases.

## Not Implemented From The Manual Yet

The following API capabilities are planned by the execution manual but are not
implemented as working behavior yet:

- `PATCH /api/events/{event_id}/status`
- standalone `/api/events` full query
- `GET /api/events/{event_id}`
- advanced filtering on flow counts and zone statistics
- database-backed aggregate statistics APIs
- database-backed Review Center workflow
- Bad Case regression and failed case conversion workflows
- industrial mAP / IDF1 / MOTA evaluation

## Placeholders For Later Phases

- `GET /api/detections`: contract-only placeholder. Use
  `GET /api/analysis-runs/{run_id}/detections` for current artifact-backed
  detection reads.
- `GET /api/tracks`: contract-only placeholder. Use
  `GET /api/analysis-runs/{run_id}/tracks` for current artifact-backed tracking
  reads.
- `GET /api/trajectories`: contract-only placeholder. Use
  `GET /api/analysis-runs/{run_id}/trajectory-points` for current
  artifact-backed trajectory reads.
- `GET /api/events`: contract-only placeholder. Use
  `GET /api/analysis-runs/{run_id}/events` for current event artifacts, or
  `/api/review` for Stage 7 review event workflows.
Stage 8EFG Evaluation APIs are routed under `/api/evaluation` and documented
above. Bad Case regression and failed case conversion remain later work.

These placeholder endpoints exist to preserve module boundaries. Standalone
event and alert center APIs remain separate from the artifact-based
`analysis-runs` list, summary, event, statistics, and alert endpoints
documented above. Review API MVP is available under `/api/review`, the Stage 7
Review Center frontend consumes it, and Stage 7F confirms the artifact-backed
Review Center MVP boundary. Stage 8CD adds artifact-backed Bad Case APIs and
frontend workflow. Stage 8EFG adds artifact-backed Evaluation APIs and frontend
workflow. Failed case conversion and regression workflow belong to later phases.
