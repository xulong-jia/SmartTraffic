# Zone Config

Zone configuration is a phase-one contract only.

Supported target zone types:

- `vehicle_lane`
- `pedestrian_area`
- `no_parking_zone`
- `danger_zone`
- `counting_zone`
- `roi`

Future implementations must snapshot zone and rule configuration per `run_id` so historical runs remain reproducible.
