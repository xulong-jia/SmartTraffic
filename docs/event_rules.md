# Event Rules

This document reflects the current implementation status after aligning with
`docs/SmartTraffic_最终版项目开发执行手册.md`.

Stage 5 is implemented as an artifact-based / in-memory MVP. The current event
rules are callback implementations over trajectory artifacts, and the video
process pipeline can generate Event / Alert artifacts after trajectory
processing. The current implementation is still not backed by database-managed
rule configuration.

The Stage 5 event rule layer currently covers the six event rules defined by the
execution manual. Zone / Event Rule configuration APIs exist as an MVP, Event
Evidence and Rule Execution artifacts include rule inputs and trigger context,
and the Alert Center supports artifact-backed query plus acknowledge / resolve /
ignore status transitions.

SmartTraffic event outputs are video-analysis signals only. They are not
law-enforcement-grade traffic violation judgments.

## Implemented Rules

### danger_zone_intrusion

Trigger condition:

- A tracked target point is inside a configured `danger_zone` polygon.

Key parameters:

- `zone_id`
- `point_type`: `bottom_center`, `center`, or `bbox` fallback
- `target_classes`
- `cooldown_seconds`
- `min_track_length`

Evidence:

- `evidence_type=zone`
- Stores zone id/type, selected point, polygon, class, track, and frame context.

Limitations:

- No keyframe snapshot generation.
- No video overlay.
- No persisted zone/rule management.

### pedestrian_in_vehicle_lane

Trigger condition:

- A tracked `person` is inside a configured `vehicle_lane` polygon.

Key parameters:

- `zone_id`
- `point_type`: `bottom_center`, `center`, or `bbox` fallback
- `target_classes`, normally `person`
- `cooldown_seconds`
- `min_track_length`

Evidence:

- `evidence_type=zone`
- Stores vehicle-lane zone, selected point, class, track, and frame context.

Limitations:

- No Review Center workflow.
- No automated safety action.
- No UI-based lane editing workflow yet.

### illegal_parking

Trigger condition:

- A vehicle remains in a configured no-parking or lane zone while speed is below
  the configured threshold and dwell time is above the configured threshold.

Key parameters:

- `zone_id`
- `point_type`
- `zone_types`
- `target_classes`
- `max_speed_px_per_frame`
- `min_dwell_time_ms`
- `min_track_length`
- `cooldown_seconds`

Evidence:

- `evidence_type=dwell`
- Stores zone, selected point, speed, dwell time, track length, and threshold
  values.

Limitations:

- Pixel-level speed and dwell only.
- No real-world speed calibration.
- Not a formal parking violation conclusion.
- No multi-camera or road-rule context.

### wrong_way_driving

Trigger condition:

- A vehicle is inside a configured `vehicle_lane` polygon and its
  `moving_angle` is clearly opposite the configured `allowed_angle`.

Key parameters:

- `zone_id`
- `point_type`: `bottom_center` or `center`
- `allowed_angle`
- `angle_tolerance`
- `min_speed_px_per_frame`
- `min_wrong_way_frames`
- `target_classes`
- `min_track_length`

Current strict logic:

```text
angle_diff = angle_difference(moving_angle, allowed_angle)
wrong_way = angle_diff >= 180 - angle_tolerance
```

Evidence:

- `evidence_type=direction`
- Stores zone, selected point, moving angle, allowed angle, angle difference,
  speed, direction vector, track length, and polygon context.

Limitations:

- No real-world direction calibration.
- No multi-frame wrong-way counter yet.
- `min_wrong_way_frames > 1` is currently unsupported.
- Lateral motion is intentionally not treated as wrong-way driving.
- Not a law-enforcement-grade direction judgment.

### flow_counting

Purpose:

- Count vehicle or person track crossings over a configured counting line as
  Stage 5 event records.

Trigger condition:

- A track segment from `previous_point` to `current_point` intersects the
  configured `line`.

Key parameters:

- `line_id`
- `line`: `[[x1, y1], [x2, y2]]`
- `direction`: `any`, `positive`, or `negative`
- `point_type`: `bottom_center` or `center`
- `count_once_per_track`
- `target_classes`
- `min_track_length`
- `cooldown_seconds`

Inputs:

- `track_id`
- `class_name`
- `frame_index`
- `timestamp_ms`

Evidence:

- `evidence_type=line_crossing`
- Stores `line_id`, `line`, `previous_point`, `current_point`,
  `crossing_direction`, `configured_direction`, `count_once_per_track`,
  `track_id`, `class_name`, `frame_index`, and `timestamp_ms`.

Runtime state:

- The callback uses EventEngine callback state to keep `previous_points` and
  `counted_keys`.
- `EventEngine.reset()` clears this state.

Limitations:

- Stage 6C now consumes generated `flow_counting` events and line-crossing
  evidence to write artifact-backed `flow_counts.json`.
- `GET /api/analysis-runs/{run_id}/flow-counts` returns that local artifact.
- No frontend flow chart yet.
- No persistent counting line config yet.
- No database-backed flow count persistence yet.
- No real-world flow calibration.

### congestion

Purpose:

- Detect low-speed, high-density vehicle states inside a configured zone as
  Stage 5 event records.

Trigger condition:

- A configured zone contains enough vehicle tracks.
- Average speed in the zone is below or equal to the configured threshold.
- The condition is satisfied for `min_congestion_frames`.

Inputs:

- `zone_id`
- `zone_types`: normally `vehicle_lane` or `roi`
- `point_type`: `bottom_center` or `center`
- `vehicle_count_threshold`
- `avg_speed_threshold`
- `min_congestion_frames`
- target vehicle classes
- frame-level `trajectory_points`

Runtime behavior:

- Runs as an aggregate rule with `rule_mode=aggregate`.
- The callback reads the full frame's `trajectory_points`.
- It emits a zone-level event with `track_id=None`.
- EventEngine callback state tracks consecutive congestion frames.
- EventEngine aggregate cooldown and dedup prevent repeated events inside the
  cooldown window.

Evidence:

- `evidence_type=zone_statistics`
- `evidence_json` includes `zone_id`, `zone_type`, `frame_index`,
  `timestamp_ms`, `vehicle_count`, `vehicle_count_threshold`,
  `avg_speed_px_per_frame`, `avg_speed_threshold`, `track_ids`,
  `class_counts`, `min_congestion_frames`, `congestion_frame_count`, and
  `polygon`.

Limitations:

- Stage 6C now consumes explicit trajectory zone data and congestion evidence
  to write artifact-backed `zone_statistics.json`.
- `GET /api/analysis-runs/{run_id}/zone-statistics` returns that local artifact.
- No frontend congestion chart yet.
- No database-backed zone statistics persistence yet.
- No real-world congestion calibration.

## Not Implemented Yet

`flow_counting` is implemented as a Stage 5 EventEngine event rule. Stage 6C
adds artifact-backed `flow_counts.json` generation and a run-scoped read API.
The database-backed aggregate flow-counting layer remains unfinished.

`congestion` is implemented as a Stage 5 EventEngine event rule. Stage 6C adds
artifact-backed `zone_statistics.json` generation and a run-scoped read API. The
database-backed zone-statistics layer remains unfinished.

## Process Integration Status

`POST /api/videos/{video_id}/process` now supports direct Event / Alert artifact
generation when `mode=detection_tracking_trajectory` is used. The process flow
is:

```text
video process
  -> detection
  -> tracking
  -> trajectory
  -> EventService / EventEngine
  -> event artifacts
  -> flow_counts.json / zone_statistics.json
  -> AlertService
  -> alert artifacts
  -> artifact index
  -> analysis-runs query
```

The process request can pass `event_rules` and `zones`. If no rules or zones are
provided, the pipeline writes stable empty event and alert artifacts rather than
inventing events; Stage 6C statistics artifacts are empty when their source
records are empty. Generated process artifacts can be queried through
`GET /api/analysis-runs/{run_id}/events`,
`GET /api/analysis-runs/{run_id}/flow-counts`,
`GET /api/analysis-runs/{run_id}/zone-statistics`, and
`GET /api/analysis-runs/{run_id}/alerts`.

This remains an artifact-based MVP. It is not the final database-backed Traffic
Analysis Center, and not a completed Review / Bad Case / Evaluation workflow.

## Current Missing Capabilities

- Multi-frame confirmation for rules that require temporal confirmation.
- Database-backed event/rule configuration.
- DirectionLineEditor and CountingLineEditor.
- Frontend flow statistics and congestion charts.
- Database-backed flow count and zone statistics persistence.
- Database-backed Traffic Analysis Center result management.
- Review / Bad Case / Evaluation workflows.

## Current Contract Boundary

Current rules consume trajectory artifacts and configured `rules` / `zones`
from request payloads or the Stage 5A in-memory config services. They do not
call YOLOv8 directly, do not run DeepSORT directly, and do not replace the
Trajectory Engine. The database-backed `event_rules`, `zones`, `flow_counts`,
and `zone_statistics` layers remain target design from the execution manual.
