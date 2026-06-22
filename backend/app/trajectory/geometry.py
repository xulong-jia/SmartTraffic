from collections.abc import Sequence


Point = tuple[float, float] | list[float]


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """Return True when a point is inside or on the boundary of a polygon."""

    if len(polygon) < 3:
        return False

    x, y = float(point[0]), float(point[1])
    inside = False
    previous = polygon[-1]

    for current in polygon:
        x1, y1 = float(previous[0]), float(previous[1])
        x2, y2 = float(current[0]), float(current[1])

        if _point_on_segment(x, y, x1, y1, x2, y2):
            return True

        intersects = (y1 > y) != (y2 > y)
        if intersects:
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current

    return inside


def _point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    epsilon: float = 1e-9,
) -> bool:
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > epsilon:
        return False
    return (
        min(x1, x2) - epsilon <= x <= max(x1, x2) + epsilon
        and min(y1, y2) - epsilon <= y <= max(y1, y2) + epsilon
    )
