from collections.abc import Mapping, Sequence
from typing import Any

from app.events.rule_callbacks.final_features import (
    zone_history_entry,
    zone_inside_duration_ms,
    zone_inside_frames,
)
from app.trajectory import geometry


SUPPORTED_POINT_TYPES = {"bottom_center", "center"}


def pedestrian_in_vehicle_lane_callback(
    rule,
    trajectory_point: dict[str, Any],
    frame_result: dict[str, Any],
    zones: list[dict[str, Any]] | None,
    engine_state: dict[str, Any],
) -> dict[str, Any]:
    class_name = _normalize_class_name(trajectory_point.get("class_name"))
    point_type = str(rule.parameters.get("point_type", "bottom_center"))

    if class_name != "person":
        return _not_matched(
            reason="class_not_person",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=None,
            inside=False,
            class_name=class_name,
        )

    min_inside_frames = int(rule.parameters.get("min_inside_frames", 1))
    min_inside_seconds = float(rule.parameters.get("min_inside_seconds", 0.0) or 0.0)
    min_inside_duration_ms = int(round(min_inside_seconds * 1000))

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
        )
    if zone.get("zone_type") != "vehicle_lane":
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
        )

    has_zone_features = bool(trajectory_point.get("zone_history"))
    history = zone_history_entry(trajectory_point, rule.zone_id)
    feature_inside_frames = zone_inside_frames(trajectory_point, rule.zone_id)
    feature_inside_duration_ms = zone_inside_duration_ms(trajectory_point, rule.zone_id)
    if not has_zone_features and min_inside_frames > 1:
        return _not_matched(
            reason="min_inside_frames_not_supported",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
        )
    if has_zone_features and history is None:
        return _not_matched(
            reason="outside_vehicle_lane",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
        )
    if history is not None and history.get("currently_inside") is False:
        return _not_matched(
            reason="outside_vehicle_lane",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=None,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
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
        )

    inside = geometry.point_in_polygon(point, polygon)
    if not inside:
        return _not_matched(
            reason="outside_vehicle_lane",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=False,
            class_name=class_name,
            polygon=polygon,
        )

    if feature_inside_frames and feature_inside_frames < min_inside_frames:
        return _not_matched(
            reason="inside_duration_not_enough",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=True,
            class_name=class_name,
            polygon=polygon,
        )
    if feature_inside_duration_ms < min_inside_duration_ms:
        return _not_matched(
            reason="inside_duration_not_enough",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            point=point,
            point_type=point_type,
            zone=zone,
            inside=True,
            class_name=class_name,
            polygon=polygon,
        )

    input_features = _input_features(
        rule=rule,
        trajectory_point=trajectory_point,
        frame_result=frame_result,
        point=point,
        point_type=point_type,
        class_name=class_name,
    )
    evidence_json = _evidence_json(
        zone=zone,
        point=point,
        point_type=point_type,
        inside=True,
        class_name=class_name,
        polygon=polygon,
    )
    evidence_json["inside_frames"] = feature_inside_frames or 1
    evidence_json["inside_duration_ms"] = feature_inside_duration_ms
    evidence_json["min_inside_frames"] = min_inside_frames
    evidence_json["min_inside_duration_ms"] = min_inside_duration_ms
    return {
        "matched": True,
        "event": {
            "event_type": "pedestrian_in_vehicle_lane",
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
                "evidence_type": "zone",
                "evidence_json": evidence_json,
            }
        ],
        "reason": "inside_vehicle_lane",
        "input_features": input_features,
        "output_result": {
            "matched": True,
            "reason": "inside_vehicle_lane",
            "zone_id": rule.zone_id,
            "point_type": point_type,
            "inside": True,
            "class_name": class_name,
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
    polygon: list[list[float]] | None = None,
) -> dict[str, Any]:
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
        ),
        "output_result": {
            "matched": False,
            "reason": reason,
            "zone_id": rule.zone_id,
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
) -> dict[str, Any]:
    return {
        "track_id": trajectory_point.get("track_id"),
        "class_name": class_name,
        "point": point,
        "point_type": point_type,
        "zone_id": rule.zone_id,
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
    }


def _evidence_json(
    *,
    zone: Mapping[str, Any],
    point: list[float],
    point_type: str,
    inside: bool,
    class_name: str,
    polygon: list[list[float]],
) -> dict[str, Any]:
    return {
        "zone_id": zone.get("zone_id"),
        "zone_type": zone.get("zone_type"),
        "point": point,
        "point_type": point_type,
        "inside": inside,
        "class_name": class_name,
        "polygon": polygon,
    }
