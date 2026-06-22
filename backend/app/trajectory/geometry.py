from collections.abc import Sequence
import math


Point = tuple[float, float] | list[float]
BBox = Sequence[float]
EPSILON = 1e-9


def bbox_center(bbox: BBox) -> tuple[float, float]:
    """Return the center point of an xyxy bbox."""

    x1, y1, x2, y2 = _validate_bbox(bbox)
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_bottom_center(bbox: BBox) -> tuple[float, float]:
    """Return the bottom-center point of an xyxy bbox."""

    x1, _, x2, y2 = _validate_bbox(bbox)
    return ((x1 + x2) / 2.0, y2)


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


def segment_intersects_line(
    p1: Point,
    p2: Point,
    q1: Point,
    q2: Point,
) -> bool:
    """Return True when two line segments intersect or touch."""

    px1, py1 = _point_xy(p1)
    px2, py2 = _point_xy(p2)
    qx1, qy1 = _point_xy(q1)
    qx2, qy2 = _point_xy(q2)

    p_is_point = _points_equal(px1, py1, px2, py2)
    q_is_point = _points_equal(qx1, qy1, qx2, qy2)
    if p_is_point and q_is_point:
        return _points_equal(px1, py1, qx1, qy1)
    if p_is_point:
        return _point_on_segment(px1, py1, qx1, qy1, qx2, qy2)
    if q_is_point:
        return _point_on_segment(qx1, qy1, px1, py1, px2, py2)

    o1 = _orientation(px1, py1, px2, py2, qx1, qy1)
    o2 = _orientation(px1, py1, px2, py2, qx2, qy2)
    o3 = _orientation(qx1, qy1, qx2, qy2, px1, py1)
    o4 = _orientation(qx1, qy1, qx2, qy2, px2, py2)

    if o1 == 0 and _point_on_segment(qx1, qy1, px1, py1, px2, py2):
        return True
    if o2 == 0 and _point_on_segment(qx2, qy2, px1, py1, px2, py2):
        return True
    if o3 == 0 and _point_on_segment(px1, py1, qx1, qy1, qx2, qy2):
        return True
    if o4 == 0 and _point_on_segment(px2, py2, qx1, qy1, qx2, qy2):
        return True

    return o1 != o2 and o3 != o4


def line_crossing_direction(
    prev_point: Point,
    curr_point: Point,
    line_start: Point,
    line_end: Point,
) -> str:
    """Return positive, negative, or none for a track crossing an oriented line."""

    if not segment_intersects_line(prev_point, curr_point, line_start, line_end):
        return "none"

    sx, sy = _point_xy(line_start)
    ex, ey = _point_xy(line_end)
    px, py = _point_xy(prev_point)
    cx, cy = _point_xy(curr_point)
    prev_side = _cross(ex - sx, ey - sy, px - sx, py - sy)
    curr_side = _cross(ex - sx, ey - sy, cx - sx, cy - sy)

    if abs(prev_side) <= EPSILON or abs(curr_side) <= EPSILON:
        return "none"
    if prev_side < 0 and curr_side > 0:
        return "positive"
    if prev_side > 0 and curr_side < 0:
        return "negative"
    return "none"


def vector_angle(vector: Sequence[float]) -> float:
    """Return the image-coordinate angle of a vector in degrees."""

    if len(vector) != 2:
        raise ValueError("vector must contain two coordinates")
    dx, dy = float(vector[0]), float(vector[1])
    if abs(dx) <= EPSILON and abs(dy) <= EPSILON:
        raise ValueError("zero vector has no angle")
    return math.degrees(math.atan2(dy, dx)) % 360.0


def angle_difference(angle_a: float, angle_b: float) -> float:
    """Return the smallest absolute difference between two degree angles."""

    diff = abs((float(angle_a) - float(angle_b)) % 360.0)
    return min(diff, 360.0 - diff)


def _validate_bbox(bbox: BBox) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain four coordinates")
    x1, y1, x2, y2 = [float(value) for value in bbox]
    if x2 < x1:
        raise ValueError("bbox x2 must be greater than or equal to x1")
    if y2 < y1:
        raise ValueError("bbox y2 must be greater than or equal to y1")
    return x1, y1, x2, y2


def _point_xy(point: Point) -> tuple[float, float]:
    if len(point) != 2:
        raise ValueError("point must contain two coordinates")
    return float(point[0]), float(point[1])


def _point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    epsilon: float = EPSILON,
) -> bool:
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > epsilon:
        return False
    return (
        min(x1, x2) - epsilon <= x <= max(x1, x2) + epsilon
        and min(y1, y2) - epsilon <= y <= max(y1, y2) + epsilon
    )


def _orientation(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> int:
    value = _cross(bx - ax, by - ay, cx - ax, cy - ay)
    if abs(value) <= EPSILON:
        return 0
    return 1 if value > 0 else -1


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _points_equal(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    epsilon: float = EPSILON,
) -> bool:
    return abs(ax - bx) <= epsilon and abs(ay - by) <= epsilon
