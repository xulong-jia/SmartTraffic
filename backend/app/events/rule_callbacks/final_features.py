from collections.abc import Mapping
from typing import Any


def zone_history_entry(
    trajectory_point: Mapping[str, Any],
    zone_id: str | None,
) -> dict[str, Any] | None:
    if zone_id is None:
        return None
    for entry in trajectory_point.get("zone_history", []) or []:
        if isinstance(entry, Mapping) and str(entry.get("zone_id")) == str(zone_id):
            return dict(entry)
    return None


def zone_inside_frames(trajectory_point: Mapping[str, Any], zone_id: str | None) -> int:
    entry = zone_history_entry(trajectory_point, zone_id)
    if entry is None or entry.get("currently_inside") is False:
        return 0
    return _int_value(entry.get("inside_frames"), default=0)


def zone_inside_duration_ms(
    trajectory_point: Mapping[str, Any],
    zone_id: str | None,
) -> int:
    entry = zone_history_entry(trajectory_point, zone_id)
    if entry is None or entry.get("currently_inside") is False:
        return 0
    return _int_value(entry.get("inside_duration_ms"), default=0)


def line_crossing(
    trajectory_point: Mapping[str, Any],
    line_id: str,
    direction: str,
) -> dict[str, Any] | None:
    for crossing in trajectory_point.get("line_crossings", []) or []:
        if not isinstance(crossing, Mapping):
            continue
        if str(crossing.get("line_id")) != str(line_id):
            continue
        crossing_direction = str(crossing.get("direction"))
        if direction != "any" and crossing_direction != direction:
            continue
        return dict(crossing)
    return None


def confirm_state(
    engine_state: dict[str, Any],
    *,
    namespace: str,
    key: tuple[Any, ...],
    matched: bool,
    required_frames: int,
) -> int:
    state = engine_state.setdefault("state", {}).setdefault(namespace, {})
    count_key = "|".join(str(item) for item in key)
    if not matched:
        state[count_key] = 0
        return 0
    state[count_key] = int(state.get(count_key, 0)) + 1
    return int(state[count_key])


def line_cooldown_active(
    engine_state: dict[str, Any],
    *,
    rule_id: str,
    line_id: str,
    track_id: Any,
    frame_index: Any,
    cooldown_frames: int,
) -> bool:
    if cooldown_frames <= 0:
        return False
    state = engine_state.setdefault("state", {}).setdefault("flow_counting_final", {})
    key = f"{rule_id}|{line_id}|{track_id}"
    current = _int_value(frame_index, default=0)
    last = state.get(key)
    if last is not None and current - int(last) < cooldown_frames:
        return True
    state[key] = current
    return False


def _int_value(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
