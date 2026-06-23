# Zone Config

Zone configuration is currently a contract and rule-input boundary, not a
completed Zone & Rule Config product module.

Current state:

- Zone and rule configuration is mainly provided through rule params / `zones`
  arguments or documented contracts.
- Implemented Stage 5 rules can read `zones` parameters.
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
