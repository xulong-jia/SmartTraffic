from app.events.rule_callbacks.danger_zone import danger_zone_intrusion_callback


DEFAULT_RULE_CALLBACKS = {
    "danger_zone_intrusion": danger_zone_intrusion_callback,
}
