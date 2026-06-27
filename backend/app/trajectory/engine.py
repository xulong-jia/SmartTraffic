from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from app.trajectory import features, geometry


class TrajectoryEngine:
    """In-memory track history cache and trajectory feature generator."""

    def __init__(
        self,
        fps: float | None = None,
        direction_window: int = 2,
        dwell_speed_threshold: float = 1.0,
        max_history_points: int | None = None,
        output_states: set[str] | None = None,
    ) -> None:
        if direction_window < 2:
            raise ValueError("direction_window must be at least 2")
        if dwell_speed_threshold < 0:
            raise ValueError("dwell_speed_threshold must be non-negative")
        if max_history_points is not None and max_history_points < 1:
            raise ValueError("max_history_points must be positive")

        self.fps = fps
        self.direction_window = direction_window
        self.dwell_speed_threshold = dwell_speed_threshold
        self.max_history_points = max_history_points
        self.output_states = output_states if output_states is not None else {"confirmed"}
        self._tracks: dict[int, dict[str, Any]] = {}
        self._total_trajectory_points = 0

    def update(
        self,
        frame_result: Mapping[str, Any],
        zones: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Update track history from one tracking frame and return trajectory points."""

        if "frame_index" not in frame_result:
            raise ValueError("frame_index is required")

        frame_index = int(frame_result["frame_index"])
        timestamp_ms = frame_result.get("timestamp_ms")
        tracks = frame_result.get("tracks", []) or []
        trajectory_points: list[dict[str, Any]] = []

        for track in tracks:
            trajectory_point = self._update_track(
                track=track,
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                zones=zones or [],
            )
            if trajectory_point is not None:
                trajectory_points.append(trajectory_point)

        return {
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "trajectory_points": trajectory_points,
        }

    def reset(self) -> None:
        """Clear all cached track state."""

        self._tracks.clear()
        self._total_trajectory_points = 0

    def get_track_state(self, track_id: int) -> dict[str, Any] | None:
        """Return a copy of a cached track state."""

        state = self._tracks.get(int(track_id))
        if state is None:
            return None
        return deepcopy(state)

    def get_summary(self) -> dict[str, Any]:
        """Return a deterministic summary of cached trajectory state."""

        track_lengths = [len(state["points"]) for state in self._tracks.values()]
        state_counts: dict[str, int] = {}
        for state in self._tracks.values():
            track_state = str(state.get("state", "unknown"))
            state_counts[track_state] = state_counts.get(track_state, 0) + 1

        return {
            "total_tracks_seen": len(self._tracks),
            "active_track_ids": sorted(self._tracks),
            "total_trajectory_points": self._total_trajectory_points,
            "track_state_counts": dict(sorted(state_counts.items())),
            "max_track_length": max(track_lengths) if track_lengths else 0,
            "avg_track_length": (
                round(sum(track_lengths) / len(track_lengths), 6)
                if track_lengths
                else 0.0
            ),
        }

    def _update_track(
        self,
        track: Mapping[str, Any],
        frame_index: int,
        timestamp_ms: int | float | None,
        zones: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        track_id = _require_track_id(track)
        bbox = _normalize_bbox(track.get("bbox"))
        center = _normalize_center(track.get("center"), bbox)
        bottom_center = geometry.bbox_bottom_center(bbox)
        state = str(track.get("state", "confirmed"))

        track_state = self._tracks.setdefault(
            track_id,
            {
                "track_id": track_id,
                "class_id": track.get("class_id"),
                "class_name": str(track.get("class_name", "")),
                "points": [],
                "last_bbox": None,
                "last_seen_frame": None,
                "last_seen_timestamp_ms": None,
                "state": state,
                "dwell_time_ms": 0,
                "zone_history_by_id": {},
                "line_last_crossing_frame": {},
                "last_center": None,
                "last_bottom_center": None,
            },
        )
        track_state["class_id"] = track.get("class_id")
        track_state["class_name"] = str(track.get("class_name", ""))
        track_state["last_bbox"] = list(bbox)
        track_state["state"] = state

        if state not in self.output_states:
            return None

        point = {
            "x": center[0],
            "y": center[1],
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
        }
        previous_point = track_state["points"][-1] if track_state["points"] else None
        previous_center = track_state.get("last_center")
        previous_bottom_center = track_state.get("last_bottom_center")
        track_state["points"].append(point)
        if (
            self.max_history_points is not None
            and len(track_state["points"]) > self.max_history_points
        ):
            track_state["points"] = track_state["points"][-self.max_history_points :]

        track_state["last_seen_frame"] = frame_index
        track_state["last_seen_timestamp_ms"] = timestamp_ms
        track_state["dwell_time_ms"] = features.compute_dwell_time(
            track_state["points"],
            speed_threshold=self.dwell_speed_threshold,
            fps=self.fps,
        )

        speed = _compute_point_speed(
            previous_point=previous_point,
            current_point=point,
            fps=self.fps,
        )
        direction_vector = features.compute_direction_vector(
            track_state["points"],
            window_size=self.direction_window,
        )
        moving_angle = features.compute_moving_angle(
            track_state["points"],
            window_size=self.direction_window,
        )
        direction_consistency = features.compute_direction_consistency(
            track_state["points"],
            window_size=max(3, self.direction_window),
        )
        zone_features = _compute_zone_features(
            track_state=track_state,
            class_name=str(track.get("class_name", "")),
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            center=[center[0], center[1]],
            bottom_center=[bottom_center[0], bottom_center[1]],
            zones=zones,
            fps=self.fps,
        )
        line_crossings = _compute_line_crossings(
            track_state=track_state,
            previous_point=previous_point,
            previous_center=previous_center,
            previous_bottom_center=previous_bottom_center,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            center=[center[0], center[1]],
            bottom_center=[bottom_center[0], bottom_center[1]],
            zones=zones,
        )
        track_state["last_center"] = [center[0], center[1]]
        track_state["last_bottom_center"] = [bottom_center[0], bottom_center[1]]
        self._total_trajectory_points += 1

        return {
            "track_id": track_id,
            "class_id": track.get("class_id"),
            "class_name": str(track.get("class_name", "")),
            "confidence": float(track.get("confidence", 0.0)),
            "bbox": list(bbox),
            "center": [center[0], center[1]],
            "bottom_center": [bottom_center[0], bottom_center[1]],
            "state": state,
            "speed_px_per_frame": speed["speed_px_per_frame"],
            "speed_px_per_second": speed["speed_px_per_second"],
            "direction_vector": _list_or_none(direction_vector),
            "moving_angle": moving_angle,
            "direction_consistency": direction_consistency,
            "center_shift_px": speed["speed_px_per_frame"],
            "dwell_time_ms": track_state["dwell_time_ms"],
            "zone_ids": zone_features["zone_ids"],
            "zone_history": zone_features["zone_history"],
            "lane_relation": zone_features["lane_relation"],
            "line_crossings": line_crossings,
            "track_length": features.compute_track_length(track_state["points"]),
            "last_seen_frame": frame_index,
            "last_seen_timestamp_ms": timestamp_ms,
        }


def _require_track_id(track: Mapping[str, Any]) -> int:
    if "track_id" not in track:
        raise ValueError("track_id is required")
    return int(track["track_id"])


def _normalize_bbox(raw_bbox: Any) -> tuple[float, float, float, float]:
    if raw_bbox is None:
        raise ValueError("bbox is required")
    if not isinstance(raw_bbox, Sequence):
        raise ValueError("bbox must contain four coordinates")
    x1, y1 = geometry.bbox_center(raw_bbox)
    bottom_x, bottom_y = geometry.bbox_bottom_center(raw_bbox)
    half_width = bottom_x - float(raw_bbox[0])
    return (
        x1 - half_width,
        float(raw_bbox[1]),
        x1 + half_width,
        bottom_y,
    )


def _normalize_center(
    raw_center: Any,
    bbox: Sequence[float],
) -> tuple[float, float]:
    if raw_center is None:
        return geometry.bbox_center(bbox)
    if not isinstance(raw_center, Sequence) or len(raw_center) < 2:
        raise ValueError("center must contain two coordinates")
    return float(raw_center[0]), float(raw_center[1])


def _compute_point_speed(
    previous_point: Mapping[str, Any] | None,
    current_point: Mapping[str, Any],
    fps: float | None,
) -> dict[str, float | None]:
    if previous_point is None:
        return {"speed_px_per_frame": 0.0, "speed_px_per_second": None}

    previous_timestamp = previous_point.get("timestamp_ms")
    current_timestamp = current_point.get("timestamp_ms")
    timestamp_delta_ms: float | None = None
    if previous_timestamp is not None and current_timestamp is not None:
        timestamp_delta_ms = float(current_timestamp) - float(previous_timestamp)
    return features.compute_speed(
        previous_point,
        current_point,
        fps=fps,
        timestamp_delta_ms=timestamp_delta_ms,
    )


def _list_or_none(values: tuple[float, float] | None) -> list[float] | None:
    if values is None:
        return None
    return [float(values[0]), float(values[1])]


def _compute_zone_features(
    *,
    track_state: dict[str, Any],
    class_name: str,
    frame_index: int,
    timestamp_ms: int | float | None,
    center: list[float],
    bottom_center: list[float],
    zones: list[dict[str, Any]],
    fps: float | None,
) -> dict[str, Any]:
    if not zones:
        return {"zone_ids": [], "zone_history": [], "lane_relation": {}}

    current_zone_ids: list[str] = []
    zone_membership: dict[str, dict[str, Any]] = {}
    history_by_id: dict[str, dict[str, Any]] = track_state.setdefault(
        "zone_history_by_id",
        {},
    )
    previous_inside_by_id = {
        zone_id: bool(history.get("currently_inside"))
        for zone_id, history in history_by_id.items()
    }

    for history in history_by_id.values():
        history["currently_inside"] = False

    for zone in zones:
        zone_id = _zone_id(zone)
        if zone_id is None or zone.get("enabled", True) is False:
            continue
        polygon = _normalize_polygon(zone.get("polygon"))
        if polygon is None:
            continue
        point_type = _point_strategy(zone)
        point = bottom_center if point_type == "bottom_center" else center
        inside = geometry.point_in_polygon(point, polygon)
        zone_membership[zone_id] = {
            "zone_id": zone_id,
            "zone_type": str(zone.get("zone_type", "")),
            "inside": inside,
            "point_type": point_type,
            "point": [float(point[0]), float(point[1])],
        }
        if not inside:
            continue

        current_zone_ids.append(zone_id)
        history = history_by_id.setdefault(
            zone_id,
            {
                "zone_id": zone_id,
                "zone_type": str(zone.get("zone_type", "")),
                "first_seen_frame": frame_index,
                "first_seen_timestamp_ms": timestamp_ms,
                "last_seen_frame": frame_index,
                "last_seen_timestamp_ms": timestamp_ms,
                "inside_frames": 0,
                "inside_duration_ms": 0,
                "currently_inside": False,
            },
        )
        previous_timestamp = history.get("last_seen_timestamp_ms")
        previous_frame = history.get("last_seen_frame")
        if previous_inside_by_id.get(zone_id) is True:
            history["inside_duration_ms"] = int(history.get("inside_duration_ms", 0)) + (
                _time_delta_ms(
                    previous_timestamp=previous_timestamp,
                    current_timestamp=timestamp_ms,
                    previous_frame=previous_frame,
                    current_frame=frame_index,
                    fps=fps,
                )
            )
        history["zone_type"] = str(zone.get("zone_type", ""))
        history["last_seen_frame"] = frame_index
        history["last_seen_timestamp_ms"] = timestamp_ms
        history["inside_frames"] = int(history.get("inside_frames", 0)) + 1
        history["currently_inside"] = True

    vehicle_classes = {"car", "truck", "bus", "motorcycle", "bicycle"}
    current_vehicle_lane_ids = [
        zone_id
        for zone_id in current_zone_ids
        if zone_membership.get(zone_id, {}).get("zone_type") == "vehicle_lane"
    ]
    current_no_parking_zone_ids = [
        zone_id
        for zone_id in current_zone_ids
        if zone_membership.get(zone_id, {}).get("zone_type") == "no_parking_zone"
    ]
    current_danger_zone_ids = [
        zone_id
        for zone_id in current_zone_ids
        if zone_membership.get(zone_id, {}).get("zone_type") == "danger_zone"
    ]
    normalized_class = class_name.strip().lower()
    lane_relation = {
        "current_vehicle_lane_ids": current_vehicle_lane_ids,
        "current_no_parking_zone_ids": current_no_parking_zone_ids,
        "current_danger_zone_ids": current_danger_zone_ids,
        "person_in_vehicle_lane": normalized_class == "person"
        and bool(current_vehicle_lane_ids),
        "vehicle_in_no_parking_zone": normalized_class in vehicle_classes
        and bool(current_no_parking_zone_ids),
        "object_in_danger_zone": bool(current_danger_zone_ids),
        "zone_membership": zone_membership,
    }
    return {
        "zone_ids": current_zone_ids,
        "zone_history": [
            dict(history)
            for _, history in sorted(history_by_id.items(), key=lambda item: item[0])
        ],
        "lane_relation": lane_relation,
    }


def _compute_line_crossings(
    *,
    track_state: dict[str, Any],
    previous_point: Mapping[str, Any] | None,
    previous_center: Any,
    previous_bottom_center: Any,
    frame_index: int,
    timestamp_ms: int | float | None,
    center: list[float],
    bottom_center: list[float],
    zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if previous_point is None:
        return []

    crossings: list[dict[str, Any]] = []
    last_crossing_frame = track_state.setdefault("line_last_crossing_frame", {})
    for zone in zones:
        line = _normalize_line(
            zone.get("line")
            or zone.get("counting_line")
            or zone.get("direction_line")
        )
        if line is None:
            continue
        line_id = str(zone.get("line_id") or _zone_id(zone) or "line")
        point_type = _point_strategy(zone)
        previous_raw = previous_bottom_center if point_type == "bottom_center" else previous_center
        if isinstance(previous_raw, Sequence) and len(previous_raw) >= 2:
            previous_selected = [float(previous_raw[0]), float(previous_raw[1])]
        else:
            previous_selected = [float(previous_point["x"]), float(previous_point["y"])]
        current_selected = bottom_center if point_type == "bottom_center" else center
        direction = geometry.line_crossing_direction(
            previous_selected,
            current_selected,
            line[0],
            line[1],
        )
        if direction not in {"positive", "negative"}:
            continue
        cooldown_frames = int(zone.get("cooldown_frames") or 0)
        previous_crossing_frame = last_crossing_frame.get(line_id)
        if (
            previous_crossing_frame is not None
            and cooldown_frames > 0
            and frame_index - int(previous_crossing_frame) < cooldown_frames
        ):
            continue
        last_crossing_frame[line_id] = frame_index
        crossings.append(
            {
                "line_id": line_id,
                "zone_id": _zone_id(zone),
                "line_type": str(zone.get("line_type") or "counting"),
                "direction": direction,
                "frame_index": frame_index,
                "timestamp_ms": timestamp_ms,
                "previous_point": previous_selected,
                "current_point": [float(current_selected[0]), float(current_selected[1])],
            }
        )
    return crossings


def _zone_id(zone: Mapping[str, Any]) -> str | None:
    value = zone.get("zone_id") or zone.get("id")
    if value is None:
        return None
    return str(value)


def _point_strategy(zone: Mapping[str, Any]) -> str:
    value = str(zone.get("point_strategy") or zone.get("point_type") or "bottom_center")
    return "center" if value == "center" else "bottom_center"


def _normalize_polygon(value: Any) -> list[list[float]] | None:
    if value is None or isinstance(value, str | bytes):
        return None
    if not isinstance(value, Sequence) or len(value) < 3:
        return None
    polygon: list[list[float]] = []
    for point in value:
        if not isinstance(point, Sequence) or len(point) < 2:
            return None
        polygon.append([float(point[0]), float(point[1])])
    return polygon


def _normalize_line(value: Any) -> list[list[float]] | None:
    if value is None or isinstance(value, str | bytes):
        return None
    if isinstance(value, Mapping):
        if value.get("enabled", True) is False:
            return None
        value = [value.get("start_point"), value.get("end_point")]
    if not isinstance(value, Sequence) or len(value) != 2:
        return None
    start, end = value
    if not isinstance(start, Sequence) or not isinstance(end, Sequence):
        return None
    if len(start) < 2 or len(end) < 2:
        return None
    return [[float(start[0]), float(start[1])], [float(end[0]), float(end[1])]]


def _time_delta_ms(
    *,
    previous_timestamp: Any,
    current_timestamp: Any,
    previous_frame: Any,
    current_frame: int,
    fps: float | None,
) -> int:
    if previous_timestamp is not None and current_timestamp is not None:
        delta = float(current_timestamp) - float(previous_timestamp)
        if delta > 0:
            return int(round(delta))
    if fps is not None and float(fps) > 0:
        frame_delta = 1
        if previous_frame is not None:
            frame_delta = max(1, int(current_frame) - int(previous_frame))
        return int(round((1000.0 / float(fps)) * frame_delta))
    return 0
