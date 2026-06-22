# Event Rules

Event rules are not implemented in phase one.

The future Event Engine must read trajectory features, zones, direction lines, counting lines, and configurable thresholds. It must not call YOLOv8 directly and must write event evidence for each generated event.

Target event types:

- `wrong_way_driving`
- `illegal_parking`
- `danger_zone_intrusion`
- `pedestrian_in_vehicle_lane`
- `congestion`
- `flow_counting`
