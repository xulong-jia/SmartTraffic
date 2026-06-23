# Event Rules

This document reflects the current implementation status after aligning with
`docs/SmartTraffic_最终版项目开发执行手册.md`.

Stage 5 is partially completed. The current event rules are artifact-based
callback implementations over trajectory artifacts. They are not yet backed by
database-managed rule configuration, a complete Zone & Rule Config UI, or a
full process mode that directly runs events and alerts.

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

## Not Implemented Yet

The execution manual still requires these Stage 5 rules:

- `congestion`
- `flow_counting`

The current `SUPPORTED_EVENT_TYPES` list may include these future event types,
but their callbacks, artifacts, tests, and service integration are not
implemented yet.

## Current Missing Capabilities

- Multi-frame confirmation for rules that require temporal confirmation.
- Persisted event/rule configuration.
- UI-based Zone & Rule Config.
- DirectionLineEditor and CountingLineEditor.
- Process mode that directly runs EventEngine and AlertService.
- Full Alert Center lifecycle: acknowledge / resolve / ignored.
- Review / Bad Case / Evaluation workflows.

## Current Contract Boundary

Current rules consume trajectory artifacts and in-memory `rules` / `zones`
parameters. They do not call YOLOv8 directly, do not run DeepSORT directly, and
do not replace the Trajectory Engine. The database-backed `event_rules`,
`zones`, `flow_counts`, and `zone_statistics` layers remain target design from
the execution manual.
