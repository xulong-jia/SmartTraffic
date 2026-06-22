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
                "zone_history": [],
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
            "dwell_time_ms": track_state["dwell_time_ms"],
            "zone_ids": [],
            "zone_history": [],
            "lane_relation": {},
            "line_crossings": [],
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
