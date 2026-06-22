import pytest

from app.trajectory import geometry


def test_bbox_center() -> None:
    assert geometry.bbox_center([10, 20, 30, 60]) == (20.0, 40.0)
    assert geometry.bbox_center([0.5, 1.5, 2.5, 5.5]) == (1.5, 3.5)


def test_bbox_bottom_center() -> None:
    assert geometry.bbox_bottom_center([10, 20, 30, 60]) == (20.0, 60.0)
    assert geometry.bbox_bottom_center([0.5, 1.5, 2.5, 5.5]) == (1.5, 5.5)


def test_bbox_helpers_reject_invalid_bbox() -> None:
    with pytest.raises(ValueError, match="four coordinates"):
        geometry.bbox_center([1, 2, 3])
    with pytest.raises(ValueError, match="four coordinates"):
        geometry.bbox_bottom_center([1, 2, 3, 4, 5])


def test_bbox_helpers_reject_reversed_bbox() -> None:
    with pytest.raises(ValueError, match="x2.*x1"):
        geometry.bbox_center([10, 1, 5, 8])
    with pytest.raises(ValueError, match="y2.*y1"):
        geometry.bbox_bottom_center([1, 10, 8, 5])


def test_point_in_polygon_inside() -> None:
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert geometry.point_in_polygon((5, 5), polygon) is True


def test_point_in_polygon_outside() -> None:
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert geometry.point_in_polygon((12, 5), polygon) is False


def test_point_in_polygon_boundary() -> None:
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert geometry.point_in_polygon((0, 5), polygon) is True
    assert geometry.point_in_polygon((10, 10), polygon) is True


def test_point_in_polygon_empty_or_invalid_polygon() -> None:
    assert geometry.point_in_polygon((1, 1), []) is False
    assert geometry.point_in_polygon((1, 1), [(0, 0), (1, 1)]) is False


def test_segment_intersects_line_crossing() -> None:
    assert geometry.segment_intersects_line((0, 0), (10, 10), (0, 10), (10, 0)) is True


def test_segment_intersects_line_no_crossing() -> None:
    assert geometry.segment_intersects_line((0, 0), (4, 0), (0, 2), (4, 2)) is False


def test_segment_intersects_line_collinear_overlap() -> None:
    assert geometry.segment_intersects_line((0, 0), (10, 0), (5, 0), (15, 0)) is True


def test_segment_intersects_line_endpoint_touch() -> None:
    assert geometry.segment_intersects_line((0, 0), (10, 0), (10, 0), (10, 8)) is True


def test_segment_intersects_line_zero_length_point_on_segment() -> None:
    assert geometry.segment_intersects_line((5, 0), (5, 0), (0, 0), (10, 0)) is True


def test_segment_intersects_line_zero_length_point_off_segment() -> None:
    assert geometry.segment_intersects_line((5, 1), (5, 1), (0, 0), (10, 0)) is False


def test_line_crossing_direction_positive_negative_none() -> None:
    line_start = (0, 0)
    line_end = (10, 0)

    assert geometry.line_crossing_direction((5, -2), (5, 2), line_start, line_end) == "positive"
    assert geometry.line_crossing_direction((5, 2), (5, -2), line_start, line_end) == "negative"
    assert geometry.line_crossing_direction((1, 2), (3, 2), line_start, line_end) == "none"


def test_line_crossing_direction_boundary_returns_none() -> None:
    line_start = (0, 0)
    line_end = (10, 0)

    assert geometry.line_crossing_direction((5, 0), (5, 2), line_start, line_end) == "none"
    assert geometry.line_crossing_direction((5, -2), (5, 0), line_start, line_end) == "none"


def test_vector_angle_cardinal_directions() -> None:
    assert geometry.vector_angle([1, 0]) == pytest.approx(0.0)
    assert geometry.vector_angle([0, 1]) == pytest.approx(90.0)
    assert geometry.vector_angle([-1, 0]) == pytest.approx(180.0)
    assert geometry.vector_angle([0, -1]) == pytest.approx(270.0)


def test_vector_angle_rejects_zero_vector() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        geometry.vector_angle([0, 0])


def test_angle_difference_wraparound() -> None:
    assert geometry.angle_difference(350, 10) == pytest.approx(20.0)
    assert geometry.angle_difference(10, 350) == pytest.approx(20.0)


def test_angle_difference_basic_cases() -> None:
    assert geometry.angle_difference(0, 180) == pytest.approx(180.0)
    assert geometry.angle_difference(45, 45) == pytest.approx(0.0)
    assert geometry.angle_difference(90, 270) == pytest.approx(180.0)
