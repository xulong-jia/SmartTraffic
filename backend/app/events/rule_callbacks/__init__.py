from app.events.rule_callbacks.danger_zone import danger_zone_intrusion_callback
from app.events.rule_callbacks.parking import illegal_parking_callback
from app.events.rule_callbacks.pedestrian_lane import pedestrian_in_vehicle_lane_callback
from app.events.rule_callbacks.wrong_way import wrong_way_driving_callback


DEFAULT_RULE_CALLBACKS = {
    "danger_zone_intrusion": danger_zone_intrusion_callback,
    "illegal_parking": illegal_parking_callback,
    "pedestrian_in_vehicle_lane": pedestrian_in_vehicle_lane_callback,
    "wrong_way_driving": wrong_way_driving_callback,
}
