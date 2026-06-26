from collections.abc import Mapping, Sequence
from typing import Any
import math

from app.trajectory import geometry


PointLike = Sequence[float] | Mapping[str, Any]


def center_from_bbox(bbox: Sequence[float]) -> tuple[float, float]:
    """Return the center point of an xyxy bbox."""

    return geometry.bbox_center(bbox)


def compute_track_length(points: list[Any]) -> int:
    """Return the number of points in a track."""

    return len(points)


def compute_speed(
    prev_point: PointLike,
    curr_point: PointLike,
    fps: float | None = None,
    timestamp_delta_ms: int | float | None = None,
) -> dict[str, float | None]:
    """Compute pixel speed per frame and optionally per second."""

    prev_x, prev_y = _extract_xy(prev_point)
    curr_x, curr_y = _extract_xy(curr_point)
    distance = math.hypot(curr_x - prev_x, curr_y - prev_y)
    speed_px_per_second: float | None = None

    if timestamp_delta_ms is not None and float(timestamp_delta_ms) > 0:
        speed_px_per_second = distance / (float(timestamp_delta_ms) / 1000.0)
    elif fps is not None and float(fps) > 0:
        speed_px_per_second = distance * float(fps)

    return {
        "speed_px_per_frame": distance,
        "speed_px_per_second": speed_px_per_second,
    }


def compute_direction_vector(
    points: list[PointLike],
    window_size: int = 2,
) -> tuple[float, float] | None:
    """Compute a raw dx/dy vector from the recent track window."""

    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    if len(points) < 2:
        return None

    recent_points = points[-window_size:]
    first_x, first_y = _extract_xy(recent_points[0])
    last_x, last_y = _extract_xy(recent_points[-1])
    return (last_x - first_x, last_y - first_y)


def compute_moving_angle(
    points: list[PointLike],
    window_size: int = 2,
) -> float | None:
    """Compute the moving angle for a recent track window."""

    direction_vector = compute_direction_vector(points, window_size=window_size)
    if direction_vector is None:
        return None
    dx, dy = direction_vector
    if abs(dx) <= geometry.EPSILON and abs(dy) <= geometry.EPSILON:
        return None
    try:
        return geometry.vector_angle(direction_vector)
    except ValueError:
        return None


def compute_direction_consistency(
    points: list[PointLike],
    window_size: int = 4,
) -> float | None:
    """Return 0..1 consistency of recent movement segment directions."""

    if len(points) < 3:
        return None
    recent_points = points[-max(3, window_size) :]
    vectors: list[tuple[float, float]] = []
    for previous, current in zip(recent_points, recent_points[1:], strict=False):
        prev_x, prev_y = _extract_xy(previous)
        curr_x, curr_y = _extract_xy(current)
        dx = curr_x - prev_x
        dy = curr_y - prev_y
        length = math.hypot(dx, dy)
        if length <= geometry.EPSILON:
            continue
        vectors.append((dx / length, dy / length))
    if len(vectors) < 2:
        return None

    mean_x = sum(vector[0] for vector in vectors) / len(vectors)
    mean_y = sum(vector[1] for vector in vectors) / len(vectors)
    consistency = math.hypot(mean_x, mean_y)
    return round(max(0.0, min(1.0, consistency)), 6)


def compute_dwell_time(
    points: list[PointLike],
    speed_threshold: float,
    fps: float | None = None,
) -> int:
    """Compute low-speed accumulated time in milliseconds."""

    if speed_threshold < 0:
        raise ValueError("speed_threshold must be non-negative")
    if len(points) < 2:
        return 0

    total_ms = 0.0
    for previous, current in zip(points, points[1:], strict=False):
        speed = compute_speed(previous, current)
        if float(speed["speed_px_per_frame"] or 0.0) > speed_threshold:
            continue

        previous_timestamp = _extract_timestamp_ms(previous)
        current_timestamp = _extract_timestamp_ms(current)
        if (
            previous_timestamp is not None
            and current_timestamp is not None
            and current_timestamp > previous_timestamp
        ):
            total_ms += current_timestamp - previous_timestamp
        elif fps is not None and float(fps) > 0:
            total_ms += 1000.0 / float(fps)

    return int(round(total_ms))


def _extract_xy(point: PointLike) -> tuple[float, float]:
    if isinstance(point, Mapping):
        if "x" in point and "y" in point:
            return float(point["x"]), float(point["y"])
        if "center_x" in point and "center_y" in point:
            return float(point["center_x"]), float(point["center_y"])
        if "center" in point:
            center = point["center"]
            if isinstance(center, Sequence) and len(center) >= 2:
                return float(center[0]), float(center[1])
        raise ValueError("point must contain x/y, center_x/center_y, or center")

    if isinstance(point, Sequence) and len(point) >= 2:
        return float(point[0]), float(point[1])

    raise ValueError("point must contain at least two coordinates")


def _extract_timestamp_ms(point: PointLike) -> float | None:
    if not isinstance(point, Mapping):
        return None
    timestamp_ms = point.get("timestamp_ms")
    if timestamp_ms is None:
        return None
    return float(timestamp_ms)
