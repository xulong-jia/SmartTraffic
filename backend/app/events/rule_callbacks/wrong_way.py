from collections.abc import Mapping, Sequence
from typing import Any

from app.trajectory import geometry


DEFAULT_VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
DEFAULT_ZONE_TYPES = ("vehicle_lane",)
SUPPORTED_POINT_TYPES = {"bottom_center", "center"}


def wrong_way_driving_callback(
    rule,
    trajectory_point: dict[str, Any],
    frame_result: dict[str, Any],
    zones: list[dict[str, Any]] | None,
    engine_state: dict[str, Any],
) -> dict[str, Any]:
    class_name = _normalize_class_name(trajectory_point.get("class_name"))
    point_type = str(rule.parameters.get("point_type", "bottom_center"))
    min_wrong_way_frames = _int_value(
        rule.parameters.get("min_wrong_way_frames"),
        default=1,
    )
    allowed_angle = _float_value(rule.parameters.get("allowed_angle"), default=0.0)
    angle_tolerance = _float_value(
        rule.parameters.get("angle_tolerance"),
        default=45.0,
    )
    min_speed_px_per_frame = _float_value(
        rule.parameters.get("min_speed_px_per_frame"),
        default=1.0,
    )
    speed_px_per_frame = _float_value(
        trajectory_point.get("speed_px_per_frame"),
        default=0.0,
    )
    speed_px_per_second = _float_or_none(trajectory_point.get("speed_px_per_second"))
    moving_angle = _float_or_none(trajectory_point.get("moving_angle"))
    direction_vector = _normalize_direction_vector(
        trajectory_point.get("direction_vector")
    )
    track_length = _int_value(trajectory_point.get("track_length"), default=0)

    if class_name not in DEFAULT_VEHICLE_CLASSES:
        return _not_matched(
            reason="class_not_vehicle",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=None,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    if min_wrong_way_frames > 1:
        return _not_matched(
            reason="min_wrong_way_frames_not_supported",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=None,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    if point_type not in SUPPORTED_POINT_TYPES:
        return _not_matched(
            reason="invalid_point_type",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=None,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    zone = _find_zone(rule.zone_id, zones or [])
    if zone is None:
        return _not_matched(
            reason="zone_not_found",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=None,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )
    if zone.get("enabled", True) is False:
        return _not_matched(
            reason="zone_disabled",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    zone_types = _normalize_zone_types(rule.parameters.get("zone_types"))
    if zone.get("zone_type") not in zone_types:
        return _not_matched(
            reason="zone_type_not_supported",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    polygon = _normalize_polygon(zone.get("polygon"))
    if polygon is None:
        return _not_matched(
            reason="invalid_zone_polygon",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    point = _select_point(point_type, trajectory_point)
    if point is None:
        return _not_matched(
            reason="point_not_available",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
        )

    inside = geometry.point_in_polygon(point, polygon)
    if not inside:
        return _not_matched(
            reason="outside_lane_zone",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
            polygon=polygon,
        )

    if moving_angle is None:
        return _not_matched(
            reason="moving_angle_not_available",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=True,
            class_name=class_name,
            moving_angle=None,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
            polygon=polygon,
        )

    if speed_px_per_frame < min_speed_px_per_frame:
        return _not_matched(
            reason="speed_below_threshold",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=True,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=None,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
            polygon=polygon,
        )

    angle_diff = geometry.angle_difference(moving_angle, allowed_angle)
    strict_wrong_way_threshold = 180.0 - angle_tolerance
    if angle_diff < strict_wrong_way_threshold:
        return _not_matched(
            reason="direction_allowed",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=True,
            class_name=class_name,
            moving_angle=moving_angle,
            allowed_angle=allowed_angle,
            angle_tolerance=angle_tolerance,
            angle_difference=angle_diff,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            min_speed_px_per_frame=min_speed_px_per_frame,
            direction_vector=direction_vector,
            track_length=track_length,
            polygon=polygon,
        )

    input_features = _input_features(
        rule=rule,
        trajectory_point=trajectory_point,
        frame_result=frame_result,
        point=point,
        point_type=point_type,
        class_name=class_name,
        moving_angle=moving_angle,
        direction_vector=direction_vector,
        speed_px_per_frame=speed_px_per_frame,
        speed_px_per_second=speed_px_per_second,
        track_length=track_length,
    )
    evidence_json = _evidence_json(
        zone=zone,
        point=point,
        point_type=point_type,
        inside=True,
        class_name=class_name,
        moving_angle=moving_angle,
        allowed_angle=allowed_angle,
        angle_tolerance=angle_tolerance,
        angle_difference=angle_diff,
        speed_px_per_frame=speed_px_per_frame,
        min_speed_px_per_frame=min_speed_px_per_frame,
        direction_vector=direction_vector,
        track_length=track_length,
        polygon=polygon,
    )
    return {
        "matched": True,
        "event": {
            "event_type": "wrong_way_driving",
            "severity": rule.severity,
            "track_id": trajectory_point.get("track_id"),
            "class_name": class_name,
            "zone_id": rule.zone_id,
            "rule_id": rule.rule_id,
            "start_frame": frame_result.get("frame_index"),
            "end_frame": frame_result.get("frame_index"),
            "start_time_ms": frame_result.get("timestamp_ms"),
            "end_time_ms": frame_result.get("timestamp_ms"),
            "confidence": 1.0,
            "status": "pending",
            "evidence": evidence_json,
        },
        "evidence": [
            {
                "evidence_type": "direction",
                "evidence_json": evidence_json,
            }
        ],
        "reason": "wrong_way_direction_detected",
        "input_features": input_features,
        "output_result": {
            "matched": True,
            "reason": "wrong_way_direction_detected",
            "zone_id": rule.zone_id,
            "moving_angle": moving_angle,
            "allowed_angle": allowed_angle,
            "angle_difference": angle_diff,
            "angle_tolerance": angle_tolerance,
            "speed_px_per_frame": speed_px_per_frame,
            "min_speed_px_per_frame": min_speed_px_per_frame,
            "strict_wrong_way_threshold": strict_wrong_way_threshold,
        },
    }


def _find_zone(zone_id: str | None, zones: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if zone_id is None:
        return None
    for zone in zones:
        if zone.get("zone_id") == zone_id:
            return zone
    return None


def _select_point(
    point_type: str,
    trajectory_point: Mapping[str, Any],
) -> list[float] | None:
    raw_point = trajectory_point.get(point_type)
    point = _normalize_point(raw_point)
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


def _normalize_class_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_zone_types(value: Any) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_ZONE_TYPES
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(item) for item in value)


def _normalize_direction_vector(value: Any) -> list[float] | None:
    if value is None or isinstance(value, str | bytes):
        return None
    if not isinstance(value, Sequence) or len(value) < 2:
        return None
    try:
        return [float(value[0]), float(value[1])]
    except (TypeError, ValueError):
        return None


def _float_value(value: Any, *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_value(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _not_matched(
    *,
    reason: str,
    rule,
    trajectory_point: Mapping[str, Any],
    frame_result: Mapping[str, Any],
    point: list[float] | None,
    point_type: str,
    zone: Mapping[str, Any] | None,
    inside: bool,
    class_name: str,
    moving_angle: float | None,
    allowed_angle: float,
    angle_tolerance: float,
    angle_difference: float | None,
    speed_px_per_frame: float,
    speed_px_per_second: float | None,
    min_speed_px_per_frame: float,
    direction_vector: list[float] | None,
    track_length: int,
    polygon: list[list[float]] | None = None,
) -> dict[str, Any]:
    strict_wrong_way_threshold = 180.0 - angle_tolerance
    return {
        "matched": False,
        "reason": reason,
        "input_features": _input_features(
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            class_name=class_name,
            moving_angle=moving_angle,
            direction_vector=direction_vector,
            speed_px_per_frame=speed_px_per_frame,
            speed_px_per_second=speed_px_per_second,
            track_length=track_length,
        ),
        "output_result": {
            "matched": False,
            "reason": reason,
            "zone_id": rule.zone_id,
            "moving_angle": moving_angle,
            "allowed_angle": allowed_angle,
            "angle_difference": angle_difference,
            "angle_tolerance": angle_tolerance,
            "speed_px_per_frame": speed_px_per_frame,
            "min_speed_px_per_frame": min_speed_px_per_frame,
            "strict_wrong_way_threshold": strict_wrong_way_threshold,
            "point_type": point_type,
            "inside": inside,
            "class_name": class_name,
            "zone_type": zone.get("zone_type") if zone is not None else None,
            "polygon": polygon,
        },
    }


def _input_features(
    *,
    rule,
    trajectory_point: Mapping[str, Any],
    frame_result: Mapping[str, Any],
    point: list[float] | None,
    point_type: str,
    class_name: str,
    moving_angle: float | None,
    direction_vector: list[float] | None,
    speed_px_per_frame: float,
    speed_px_per_second: float | None,
    track_length: int,
) -> dict[str, Any]:
    return {
        "track_id": trajectory_point.get("track_id"),
        "class_name": class_name,
        "point": point,
        "point_type": point_type,
        "zone_id": rule.zone_id,
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
        "moving_angle": moving_angle,
        "direction_vector": direction_vector,
        "speed_px_per_frame": speed_px_per_frame,
        "speed_px_per_second": speed_px_per_second,
        "track_length": track_length,
    }


def _evidence_json(
    *,
    zone: Mapping[str, Any],
    point: list[float],
    point_type: str,
    inside: bool,
    class_name: str,
    moving_angle: float,
    allowed_angle: float,
    angle_tolerance: float,
    angle_difference: float,
    speed_px_per_frame: float,
    min_speed_px_per_frame: float,
    direction_vector: list[float] | None,
    track_length: int,
    polygon: list[list[float]],
) -> dict[str, Any]:
    return {
        "zone_id": zone.get("zone_id"),
        "zone_type": zone.get("zone_type"),
        "point": point,
        "point_type": point_type,
        "inside": inside,
        "class_name": class_name,
        "moving_angle": moving_angle,
        "allowed_angle": allowed_angle,
        "angle_tolerance": angle_tolerance,
        "angle_difference": angle_difference,
        "speed_px_per_frame": speed_px_per_frame,
        "min_speed_px_per_frame": min_speed_px_per_frame,
        "direction_vector": direction_vector,
        "track_length": track_length,
        "polygon": polygon,
    }
