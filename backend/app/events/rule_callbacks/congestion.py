from collections.abc import Mapping, Sequence
from typing import Any

from app.trajectory import geometry


DEFAULT_VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
DEFAULT_ZONE_TYPES = ("vehicle_lane", "roi")
SUPPORTED_POINT_TYPES = {"bottom_center", "center"}


def congestion_callback(
    rule,
    trajectory_point: dict[str, Any] | None,
    frame_result: dict[str, Any],
    zones: list[dict[str, Any]] | None,
    engine_state: dict[str, Any],
) -> dict[str, Any]:
    point_type = str(rule.parameters.get("point_type", "bottom_center"))
    vehicle_count_threshold = _int_value(
        rule.parameters.get("vehicle_count_threshold"),
        default=5,
    )
    avg_speed_threshold = _float_value(
        rule.parameters.get("avg_speed_threshold"),
        default=2.0,
    )
    min_congestion_frames = _int_value(
        rule.parameters.get("min_congestion_frames"),
        default=1,
    )
    time_window_seconds = _float_value(
        rule.parameters.get("time_window_seconds"),
        default=0.0,
    )
    if time_window_seconds > 0 and rule.parameters.get("min_congestion_frames") is None:
        min_congestion_frames = 2
    if min_congestion_frames < 1:
        min_congestion_frames = 1

    if rule.parameters.get("rule_mode") != "aggregate" or trajectory_point is not None:
        return _not_matched(
            reason="not_aggregate_rule",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=None,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    if rule.zone_id is None:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="zone_not_configured",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=None,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    if point_type not in SUPPORTED_POINT_TYPES:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="invalid_point_type",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=None,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    zone = _find_zone(rule.zone_id, zones or [])
    if zone is None:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="zone_not_found",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=None,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    if zone.get("enabled", True) is False:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="zone_disabled",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    zone_types = _normalize_zone_types(rule.parameters.get("zone_types"))
    if zone.get("zone_type") not in zone_types:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="zone_type_not_supported",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    polygon = _normalize_polygon(zone.get("polygon"))
    if polygon is None:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="invalid_zone_polygon",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=None,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=_trajectory_point_count(frame_result),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    trajectory_points = list(frame_result.get("trajectory_points", []) or [])
    if not trajectory_points:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="no_trajectory_points",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=0,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=None,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=[],
            class_counts={},
            candidate_vehicle_count=0,
            total_trajectory_points=0,
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    stats = _collect_zone_vehicle_stats(
        rule=rule,
        trajectory_points=trajectory_points,
        point_type=point_type,
        polygon=polygon,
    )
    vehicle_count = stats["vehicle_count"]
    avg_speed_px_per_frame = stats["avg_speed_px_per_frame"]
    congestion_frame_count = _state_for_rule(engine_state, rule).get(
        "consecutive_frames",
        0,
    )

    if vehicle_count == 0:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="no_vehicle_in_zone",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=stats["track_ids"],
            class_counts=stats["class_counts"],
            candidate_vehicle_count=stats["candidate_vehicle_count"],
            total_trajectory_points=len(trajectory_points),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    if vehicle_count < vehicle_count_threshold:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="vehicle_count_below_threshold",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=stats["track_ids"],
            class_counts=stats["class_counts"],
            candidate_vehicle_count=stats["candidate_vehicle_count"],
            total_trajectory_points=len(trajectory_points),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    if avg_speed_px_per_frame is None or avg_speed_px_per_frame > avg_speed_threshold:
        _reset_state(engine_state, rule)
        return _not_matched(
            reason="avg_speed_above_threshold",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=stats["track_ids"],
            class_counts=stats["class_counts"],
            candidate_vehicle_count=stats["candidate_vehicle_count"],
            total_trajectory_points=len(trajectory_points),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=0,
        )

    state = _state_for_rule(engine_state, rule)
    frame_index = frame_result.get("frame_index")
    if state.get("last_frame_index") == frame_index:
        return _not_matched(
            reason="frame_already_evaluated",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=stats["track_ids"],
            class_counts=stats["class_counts"],
            candidate_vehicle_count=stats["candidate_vehicle_count"],
            total_trajectory_points=len(trajectory_points),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=int(state.get("consecutive_frames", 0)),
        )

    if state.get("active_start_frame") is None:
        state["active_start_frame"] = frame_index
        state["active_start_time_ms"] = frame_result.get("timestamp_ms")
    state["last_frame_index"] = frame_index
    state["consecutive_frames"] = int(state.get("consecutive_frames", 0)) + 1
    congestion_frame_count = int(state["consecutive_frames"])

    if congestion_frame_count < min_congestion_frames:
        return _not_matched(
            reason="congestion_frames_not_enough",
            rule=rule,
            frame_result=frame_result,
            point_type=point_type,
            zone=zone,
            polygon=polygon,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            track_ids=stats["track_ids"],
            class_counts=stats["class_counts"],
            candidate_vehicle_count=stats["candidate_vehicle_count"],
            total_trajectory_points=len(trajectory_points),
            min_congestion_frames=min_congestion_frames,
            congestion_frame_count=congestion_frame_count,
        )

    evidence_json = _evidence_json(
        zone=zone,
        frame_result=frame_result,
        polygon=polygon,
        vehicle_count=vehicle_count,
        vehicle_count_threshold=vehicle_count_threshold,
        avg_speed_px_per_frame=avg_speed_px_per_frame,
        avg_speed_threshold=avg_speed_threshold,
        track_ids=stats["track_ids"],
        class_counts=stats["class_counts"],
        min_congestion_frames=min_congestion_frames,
        congestion_frame_count=congestion_frame_count,
    )
    evidence_json["window_seconds"] = time_window_seconds
    input_features = _input_features(
        rule=rule,
        frame_result=frame_result,
        total_trajectory_points=len(trajectory_points),
        candidate_vehicle_count=stats["candidate_vehicle_count"],
        vehicle_track_ids=stats["track_ids"],
        class_counts=stats["class_counts"],
        point_type=point_type,
    )

    return {
        "matched": True,
        "event": {
            "event_type": "congestion",
            "severity": rule.severity,
            "track_id": None,
            "class_name": None,
            "zone_id": rule.zone_id,
            "rule_id": rule.rule_id,
            "start_frame": state.get("active_start_frame"),
            "end_frame": frame_result.get("frame_index"),
            "start_time_ms": state.get("active_start_time_ms"),
            "end_time_ms": frame_result.get("timestamp_ms"),
            "confidence": 1.0,
            "status": "pending",
            "evidence": evidence_json,
        },
        "evidence": [
            {
                "evidence_type": "zone_statistics",
                "evidence_json": evidence_json,
            }
        ],
        "reason": "congestion_detected",
        "input_features": input_features,
        "output_result": _output_result(
            matched=True,
            reason="congestion_detected",
            rule=rule,
            vehicle_count=vehicle_count,
            vehicle_count_threshold=vehicle_count_threshold,
            avg_speed_px_per_frame=avg_speed_px_per_frame,
            avg_speed_threshold=avg_speed_threshold,
            congestion_frame_count=congestion_frame_count,
            min_congestion_frames=min_congestion_frames,
        ),
    }


def _collect_zone_vehicle_stats(
    *,
    rule,
    trajectory_points: Sequence[Mapping[str, Any]],
    point_type: str,
    polygon: list[list[float]],
) -> dict[str, Any]:
    target_classes = set(rule.target_classes or DEFAULT_VEHICLE_CLASSES)
    track_ids: list[Any] = []
    speeds: list[float] = []
    class_counts: dict[str, int] = {}
    candidate_vehicle_count = 0

    for trajectory_point in trajectory_points:
        class_name = _normalize_class_name(trajectory_point.get("class_name"))
        if class_name not in target_classes:
            continue
        candidate_vehicle_count += 1
        if _int_value(trajectory_point.get("track_length"), default=0) < rule.min_track_length:
            continue
        point = _select_point(point_type, trajectory_point)
        if point is None or not geometry.point_in_polygon(point, polygon):
            continue

        track_ids.append(trajectory_point.get("track_id"))
        speeds.append(
            _float_value(trajectory_point.get("speed_px_per_frame"), default=0.0)
        )
        class_counts[class_name] = class_counts.get(class_name, 0) + 1

    avg_speed = round(sum(speeds) / len(speeds), 6) if speeds else None
    return {
        "vehicle_count": len(track_ids),
        "candidate_vehicle_count": candidate_vehicle_count,
        "avg_speed_px_per_frame": avg_speed,
        "track_ids": track_ids,
        "class_counts": dict(sorted(class_counts.items())),
    }


def _find_zone(zone_id: str | None, zones: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if zone_id is None:
        return None
    for zone in zones:
        if zone.get("zone_id") == zone_id:
            return zone
    return None


def _state_for_rule(engine_state: dict[str, Any], rule) -> dict[str, Any]:
    state = engine_state.setdefault("state", {})
    congestion_state = state.setdefault("congestion", {})
    state_key = f"{rule.rule_id}:{rule.zone_id}"
    return congestion_state.setdefault(
        state_key,
        {
            "consecutive_frames": 0,
            "active_start_frame": None,
            "active_start_time_ms": None,
            "last_frame_index": None,
        },
    )


def _reset_state(engine_state: dict[str, Any], rule) -> None:
    state = _state_for_rule(engine_state, rule)
    state["consecutive_frames"] = 0
    state["active_start_frame"] = None
    state["active_start_time_ms"] = None
    state["last_frame_index"] = None


def _select_point(
    point_type: str,
    trajectory_point: Mapping[str, Any],
) -> list[float] | None:
    point = _normalize_point(trajectory_point.get(point_type))
    if point is not None:
        return point

    bbox = trajectory_point.get("bbox")
    if bbox is None:
        return None
    try:
        if point_type == "bottom_center":
            fallback_point = geometry.bbox_bottom_center(bbox)
        else:
            fallback_point = geometry.bbox_center(bbox)
    except (TypeError, ValueError):
        return None
    return [float(fallback_point[0]), float(fallback_point[1])]


def _normalize_point(value: Any) -> list[float] | None:
    if value is None or isinstance(value, str | bytes):
        return None
    if not isinstance(value, Sequence) or len(value) < 2:
        return None
    try:
        return [float(value[0]), float(value[1])]
    except (TypeError, ValueError):
        return None


def _normalize_polygon(value: Any) -> list[list[float]] | None:
    if value is None or isinstance(value, str | bytes):
        return None
    if not isinstance(value, Sequence) or len(value) < 3:
        return None
    polygon: list[list[float]] = []
    for point in value:
        normalized_point = _normalize_point(point)
        if normalized_point is None:
            return None
        polygon.append(normalized_point)
    return polygon


def _normalize_zone_types(value: Any) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_ZONE_TYPES
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value)
    return DEFAULT_ZONE_TYPES


def _not_matched(
    *,
    reason: str,
    rule,
    frame_result: Mapping[str, Any],
    point_type: str,
    zone: Mapping[str, Any] | None,
    polygon: list[list[float]] | None,
    vehicle_count: int,
    vehicle_count_threshold: int,
    avg_speed_px_per_frame: float | None,
    avg_speed_threshold: float,
    track_ids: list[Any],
    class_counts: dict[str, int],
    candidate_vehicle_count: int,
    total_trajectory_points: int,
    min_congestion_frames: int,
    congestion_frame_count: int,
) -> dict[str, Any]:
    return {
        "matched": False,
        "reason": reason,
        "input_features": _input_features(
            rule=rule,
            frame_result=frame_result,
            total_trajectory_points=total_trajectory_points,
            candidate_vehicle_count=candidate_vehicle_count,
            vehicle_track_ids=track_ids,
            class_counts=class_counts,
            point_type=point_type,
        ),
        "output_result": {
            **_output_result(
                matched=False,
                reason=reason,
                rule=rule,
                vehicle_count=vehicle_count,
                vehicle_count_threshold=vehicle_count_threshold,
                avg_speed_px_per_frame=avg_speed_px_per_frame,
                avg_speed_threshold=avg_speed_threshold,
                congestion_frame_count=congestion_frame_count,
                min_congestion_frames=min_congestion_frames,
            ),
            "zone_type": zone.get("zone_type") if zone is not None else None,
            "point_type": point_type,
            "polygon": polygon,
            "track_ids": track_ids,
            "class_counts": class_counts,
        },
    }


def _input_features(
    *,
    rule,
    frame_result: Mapping[str, Any],
    total_trajectory_points: int,
    candidate_vehicle_count: int,
    vehicle_track_ids: list[Any],
    class_counts: dict[str, int],
    point_type: str,
) -> dict[str, Any]:
    return {
        "zone_id": rule.zone_id,
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
        "total_trajectory_points": total_trajectory_points,
        "candidate_vehicle_count": candidate_vehicle_count,
        "vehicle_track_ids": vehicle_track_ids,
        "class_counts": class_counts,
        "point_type": point_type,
    }


def _output_result(
    *,
    matched: bool,
    reason: str,
    rule,
    vehicle_count: int,
    vehicle_count_threshold: int,
    avg_speed_px_per_frame: float | None,
    avg_speed_threshold: float,
    congestion_frame_count: int,
    min_congestion_frames: int,
) -> dict[str, Any]:
    return {
        "matched": matched,
        "reason": reason,
        "zone_id": rule.zone_id,
        "vehicle_count": vehicle_count,
        "vehicle_count_threshold": vehicle_count_threshold,
        "avg_speed_px_per_frame": avg_speed_px_per_frame,
        "avg_speed_threshold": avg_speed_threshold,
        "congestion_frame_count": congestion_frame_count,
        "min_congestion_frames": min_congestion_frames,
    }


def _evidence_json(
    *,
    zone: Mapping[str, Any],
    frame_result: Mapping[str, Any],
    polygon: list[list[float]],
    vehicle_count: int,
    vehicle_count_threshold: int,
    avg_speed_px_per_frame: float | None,
    avg_speed_threshold: float,
    track_ids: list[Any],
    class_counts: dict[str, int],
    min_congestion_frames: int,
    congestion_frame_count: int,
) -> dict[str, Any]:
    return {
        "zone_id": zone.get("zone_id"),
        "zone_type": zone.get("zone_type"),
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
        "vehicle_count": vehicle_count,
        "vehicle_count_threshold": vehicle_count_threshold,
        "avg_speed_px_per_frame": avg_speed_px_per_frame,
        "avg_speed_threshold": avg_speed_threshold,
        "track_ids": track_ids,
        "class_counts": class_counts,
        "min_congestion_frames": min_congestion_frames,
        "congestion_frame_count": congestion_frame_count,
        "polygon": polygon,
    }


def _trajectory_point_count(frame_result: Mapping[str, Any]) -> int:
    return len(frame_result.get("trajectory_points", []) or [])


def _normalize_class_name(value: Any) -> str:
    return str(value or "").strip().lower()


def _int_value(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
