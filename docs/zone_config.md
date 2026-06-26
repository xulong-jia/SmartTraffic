# Zone Config

Zone configuration is DB-backed for local validation. Full Stage 3AB moved
zone and event-rule CRUD to the database, Full Stage 5AB connected the
frontend ZoneEditor to those APIs, and processing-created runs store a
run-level config snapshot in `traffic_analysis_runs.summary`.

Current state:

- Zone and rule configuration APIs are DB-backed under `/api/zones` and
  `/api/event-rules`.
- `POST /api/videos/{video_id}/process` can still receive per-run `zones` and
  `event_rules` payloads; when DB config is used, processing stores the current
  zone/rule snapshot for run reproducibility.
- The frontend ZoneEditor supports polygon, direction line, and counting line
  drawing, save/update/delete, enabled/version display, validation, loading,
  error, and empty states.
- Full Stage 5CD consumes zones in Analysis Detail overlays, including
  polygons, direction lines, counting lines, enabled state, and selected event
  zone highlighting.

Supported target zone types:

- `vehicle_lane`
- `pedestrian_area`
- `no_parking_zone`
- `danger_zone`
- `counting_zone`
- `roi`

Current boundaries:

- Geometry is pixel-space and local-video oriented; there is no camera
  calibration or real-world lane model.
- Zone / rule config is suitable for local validation, not formal traffic
  enforcement.
- Production multi-user editing, approval workflow, and enterprise permission
  controls are outside the current implementation.
