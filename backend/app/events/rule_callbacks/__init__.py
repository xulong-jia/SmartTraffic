from app.events.rule_callbacks.danger_zone import danger_zone_intrusion_callback
from app.events.rule_callbacks.pedestrian_lane import pedestrian_in_vehicle_lane_callback


DEFAULT_RULE_CALLBACKS = {
    "danger_zone_intrusion": danger_zone_intrusion_callback,
    "pedestrian_in_vehicle_lane": pedestrian_in_vehicle_lane_callback,
}
