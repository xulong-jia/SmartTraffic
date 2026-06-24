# Zone Config

Zone configuration is currently a contract and rule-input boundary, not a
completed Zone & Rule Config product module.

Current state:

- Zone and rule configuration has artifact-based / in-memory MVP APIs under
  `/api/zones` and `/api/event-rules`.
- `POST /api/videos/{video_id}/process` can also receive per-run `zones` and
  `event_rules` payloads, and implemented Stage 5 rules read those inputs.
- Full Zone Editor, DirectionLineEditor, CountingLineEditor, persisted
  configuration, and per-run config snapshot are not complete.
- The current frontend `ZoneEditor` is a placeholder shell and should not be
  treated as a finished editor workflow.

Supported target zone types:

- `vehicle_lane`
- `pedestrian_area`
- `no_parking_zone`
- `danger_zone`
- `counting_zone`
- `roi`

Future implementations must snapshot zone and rule configuration per `run_id` so historical runs remain reproducible.
