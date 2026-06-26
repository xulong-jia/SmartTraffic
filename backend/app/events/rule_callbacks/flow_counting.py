from collections.abc import Mapping, Sequence
from typing import Any

from app.events.rule_callbacks.final_features import line_cooldown_active, line_crossing
from app.trajectory import geometry


SUPPORTED_DIRECTIONS = {"any", "positive", "negative"}
SUPPORTED_POINT_TYPES = {"bottom_center", "center"}


def flow_counting_callback(
    rule,
    trajectory_point: dict[str, Any],
    frame_result: dict[str, Any],
    zones: list[dict[str, Any]] | None,
    engine_state: dict[str, Any],
) -> dict[str, Any]:
    line_id = str(rule.parameters.get("line_id", "counting_line"))
    line = _normalize_line(rule.parameters.get("line"))
    direction = str(rule.parameters.get("direction", "any"))
    point_type = str(rule.parameters.get("point_type", "bottom_center"))
    count_once_per_track = _bool_value(
        rule.parameters.get("count_once_per_track"),
        default=True,
    )
    same_track_cooldown_frames = int(rule.parameters.get("same_track_cooldown_frames") or 0)
    track_id = trajectory_point.get("track_id")
    class_name = str(trajectory_point.get("class_name", ""))

    crossing_from_features = line_crossing(trajectory_point, line_id, direction)
    if crossing_from_features is not None:
        if line_cooldown_active(
            engine_state,
            rule_id=rule.rule_id,
            line_id=line_id,
            track_id=track_id,
            frame_index=frame_result.get("frame_index"),
            cooldown_frames=same_track_cooldown_frames,
        ):
            return _not_matched(
                reason="same_track_line_cooldown",
                rule=rule,
                trajectory_point=trajectory_point,
                frame_result=frame_result,
                line_id=line_id,
                line=line,
                point_type=point_type,
                current_point=crossing_from_features.get("current_point"),
                previous_point=crossing_from_features.get("previous_point"),
                crossing_direction=str(crossing_from_features.get("direction")),
                configured_direction=direction,
                count_once_per_track=count_once_per_track,
                already_counted=True,
                crossed=True,
            )
        crossing_direction = str(crossing_from_features.get("direction"))
        evidence_json = {
            "line_id": line_id,
            "counting_line_id": line_id,
            "direction": crossing_direction,
            "crossing_direction": crossing_direction,
            "configured_direction": direction,
            "track_id": track_id,
            "class_name": class_name,
            "frame_index": frame_result.get("frame_index"),
            "timestamp_ms": frame_result.get("timestamp_ms"),
            "line_crossing": crossing_from_features,
        }
        return {
            "matched": True,
            "event": {
                "event_type": "flow_counting",
                "severity": rule.severity,
                "track_id": track_id,
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
                    "evidence_type": "line_crossing",
                    "evidence_json": evidence_json,
                }
            ],
            "reason": "line_crossed",
            "input_features": {
                "track_id": track_id,
                "class_name": class_name,
                "line_id": line_id,
                "line_crossings": trajectory_point.get("line_crossings", []),
            },
            "output_result": {
                "matched": True,
                "reason": "line_crossed",
                "line_id": line_id,
                "crossed": True,
                "crossing_direction": crossing_direction,
                "configured_direction": direction,
                "already_counted": False,
                "count_once_per_track": count_once_per_track,
            },
        }

    if line is None:
        return _not_matched(
            reason="invalid_line",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=None,
            point_type=point_type,
            current_point=None,
            previous_point=None,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    if direction not in SUPPORTED_DIRECTIONS:
        return _not_matched(
            reason="unsupported_direction",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=None,
            previous_point=None,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    if point_type not in SUPPORTED_POINT_TYPES:
        return _not_matched(
            reason="invalid_point_type",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=None,
            previous_point=None,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    current_point = _select_point(point_type, trajectory_point)
    if current_point is None:
        return _not_matched(
            reason="point_not_available",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=None,
            previous_point=None,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    flow_state = _flow_state(engine_state)
    previous_points = flow_state.setdefault("previous_points", {})
    counted_keys = flow_state.setdefault("counted_keys", set())
    previous_key = (rule.rule_id, track_id, point_type)
    counted_key = (rule.rule_id, line_id, track_id)
    previous_point = previous_points.get(previous_key)

    if previous_point is None:
        previous_points[previous_key] = current_point
        return _not_matched(
            reason="previous_point_not_available",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=current_point,
            previous_point=None,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    crossed = geometry.segment_intersects_line(
        previous_point,
        current_point,
        line[0],
        line[1],
    )
    if not crossed:
        previous_points[previous_key] = current_point
        return _not_matched(
            reason="line_not_crossed",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=current_point,
            previous_point=previous_point,
            crossing_direction=None,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=False,
        )

    crossing_direction = geometry.line_crossing_direction(
        previous_point,
        current_point,
        line[0],
        line[1],
    )
    if crossing_direction not in {"positive", "negative"}:
        previous_points[previous_key] = current_point
        return _not_matched(
            reason="direction_unknown",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=current_point,
            previous_point=previous_point,
            crossing_direction=crossing_direction,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=True,
        )

    if direction != "any" and crossing_direction != direction:
        previous_points[previous_key] = current_point
        return _not_matched(
            reason="direction_not_matched",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=current_point,
            previous_point=previous_point,
            crossing_direction=crossing_direction,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=False,
            crossed=True,
        )

    if count_once_per_track and counted_key in counted_keys:
        previous_points[previous_key] = current_point
        return _not_matched(
            reason="already_counted",
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            point_type=point_type,
            current_point=current_point,
            previous_point=previous_point,
            crossing_direction=crossing_direction,
            configured_direction=direction,
            count_once_per_track=count_once_per_track,
            already_counted=True,
            crossed=True,
        )

    previous_points[previous_key] = current_point
    if count_once_per_track:
        counted_keys.add(counted_key)

    evidence_json = _evidence_json(
        line_id=line_id,
        line=line,
        previous_point=previous_point,
        current_point=current_point,
        point_type=point_type,
        crossing_direction=crossing_direction,
        configured_direction=direction,
        count_once_per_track=count_once_per_track,
        track_id=track_id,
        class_name=class_name,
        frame_result=frame_result,
    )
    input_features = _input_features(
        rule=rule,
        trajectory_point=trajectory_point,
        frame_result=frame_result,
        line_id=line_id,
        line=line,
        previous_point=previous_point,
        current_point=current_point,
        point_type=point_type,
    )

    return {
        "matched": True,
        "event": {
            "event_type": "flow_counting",
            "severity": rule.severity,
            "track_id": track_id,
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
                "evidence_type": "line_crossing",
                "evidence_json": evidence_json,
            }
        ],
        "reason": "line_crossed",
        "input_features": input_features,
        "output_result": {
            "matched": True,
            "reason": "line_crossed",
            "line_id": line_id,
            "crossed": True,
            "crossing_direction": crossing_direction,
            "configured_direction": direction,
            "already_counted": False,
            "count_once_per_track": count_once_per_track,
        },
    }


def _flow_state(engine_state: dict[str, Any]) -> dict[str, Any]:
    state = engine_state.setdefault("state", {})
    return state.setdefault("flow_counting", {})


def _normalize_line(value: Any) -> list[list[float]] | None:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return None
    if len(value) != 2:
        return None
    start = _normalize_point(value[0])
    end = _normalize_point(value[1])
    if start is None or end is None:
        return None
    if abs(start[0] - end[0]) <= geometry.EPSILON and abs(start[1] - end[1]) <= geometry.EPSILON:
        return None
    return [start, end]


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


def _bool_value(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(value)


def _not_matched(
    *,
    reason: str,
    rule,
    trajectory_point: Mapping[str, Any],
    frame_result: Mapping[str, Any],
    line_id: str,
    line: list[list[float]] | None,
    point_type: str,
    current_point: list[float] | None,
    previous_point: list[float] | None,
    crossing_direction: str | None,
    configured_direction: str,
    count_once_per_track: bool,
    already_counted: bool,
    crossed: bool,
) -> dict[str, Any]:
    return {
        "matched": False,
        "reason": reason,
        "input_features": _input_features(
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            line_id=line_id,
            line=line,
            previous_point=previous_point,
            current_point=current_point,
            point_type=point_type,
        ),
        "output_result": {
            "matched": False,
            "reason": reason,
            "line_id": line_id,
            "crossed": crossed,
            "crossing_direction": crossing_direction,
            "configured_direction": configured_direction,
            "already_counted": already_counted,
            "count_once_per_track": count_once_per_track,
        },
    }


def _input_features(
    *,
    rule,
    trajectory_point: Mapping[str, Any],
    frame_result: Mapping[str, Any],
    line_id: str,
    line: list[list[float]] | None,
    previous_point: list[float] | None,
    current_point: list[float] | None,
    point_type: str,
) -> dict[str, Any]:
    return {
        "track_id": trajectory_point.get("track_id"),
        "class_name": trajectory_point.get("class_name"),
        "previous_point": previous_point,
        "current_point": current_point,
        "point_type": point_type,
        "line_id": line_id,
        "line": line,
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
    }


def _evidence_json(
    *,
    line_id: str,
    line: list[list[float]],
    previous_point: list[float],
    current_point: list[float],
    point_type: str,
    crossing_direction: str,
    configured_direction: str,
    count_once_per_track: bool,
    track_id: Any,
    class_name: str,
    frame_result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "line_id": line_id,
        "counting_line_id": line_id,
        "direction": crossing_direction,
        "line": line,
        "previous_point": previous_point,
        "current_point": current_point,
        "point_type": point_type,
        "crossing_direction": crossing_direction,
        "configured_direction": configured_direction,
        "count_once_per_track": count_once_per_track,
        "track_id": track_id,
        "class_name": class_name,
        "frame_index": frame_result.get("frame_index"),
        "timestamp_ms": frame_result.get("timestamp_ms"),
    }
