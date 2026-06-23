# Event Rules

This document reflects the current implementation status after aligning with
`docs/SmartTraffic_最终版项目开发执行手册.md`.

Stage 5 is partially completed. The current event rules are artifact-based
callback implementations over trajectory artifacts. They are not yet backed by
database-managed rule configuration, a complete Zone & Rule Config UI, or a
full process mode that directly runs events and alerts.

The Stage 5 event rule layer currently covers the six event rules defined by the
execution manual. Stage 5 is still not fully complete because system-level
capabilities such as persisted zone/rule configuration, direct process pipeline
integration, and the full Alert Center lifecycle remain unfinished.

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

- No `flow_counts.json` yet.
- No `/api/analysis-runs/{run_id}/flow-counts` API yet.
- No per-minute aggregate stats yet.
- No frontend flow chart yet.
- No persistent counting line config yet.
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

- No `zone_statistics.json` yet.
- No `/api/analysis-runs/{run_id}/zone-statistics` API yet.
- No frontend congestion chart yet.
- No database-backed zone statistics persistence yet.
- No real-world congestion calibration.

## Not Implemented Yet

`flow_counting` is implemented as a Stage 5 EventEngine event rule, but the
manual's later aggregate flow-counting outputs remain unfinished.

`congestion` is implemented as a Stage 5 EventEngine event rule, but the
manual's later aggregate zone-statistics outputs remain unfinished.

## Current Missing Capabilities

- Multi-frame confirmation for rules that require temporal confirmation.
- Persisted event/rule configuration.
- UI-based Zone & Rule Config.
- DirectionLineEditor and CountingLineEditor.
- Aggregate `flow_counts.json` and flow statistics APIs.
- Aggregate `zone_statistics.json` and zone statistics APIs.
- Process mode that directly runs EventEngine and AlertService.
- Full Alert Center lifecycle: acknowledge / resolve / ignored.
- Review / Bad Case / Evaluation workflows.

## Current Contract Boundary

Current rules consume trajectory artifacts and in-memory `rules` / `zones`
parameters. They do not call YOLOv8 directly, do not run DeepSORT directly, and
do not replace the Trajectory Engine. The database-backed `event_rules`,
`zones`, `flow_counts`, and `zone_statistics` layers remain target design from
the execution manual.
