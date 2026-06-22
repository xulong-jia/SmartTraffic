from app.trajectory.geometry import point_in_polygon


def test_point_in_polygon_detects_inside_outside_and_boundary_points() -> None:
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]

    assert point_in_polygon((5, 5), polygon) is True
    assert point_in_polygon((12, 5), polygon) is False
    assert point_in_polygon((0, 5), polygon) is True
