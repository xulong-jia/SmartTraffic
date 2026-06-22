import pytest

from app.trajectory import features


def test_center_from_bbox_uses_geometry_contract() -> None:
    assert features.center_from_bbox([0, 0, 10, 20]) == (5.0, 10.0)


def test_compute_track_length() -> None:
    assert features.compute_track_length([]) == 0
    assert features.compute_track_length([(0, 0), (1, 1), (2, 2)]) == 3


def test_compute_speed_px_per_frame() -> None:
    result = features.compute_speed((0, 0), (3, 4))

    assert result["speed_px_per_frame"] == pytest.approx(5.0)
    assert result["speed_px_per_second"] is None


def test_compute_speed_px_per_second_with_timestamp_delta() -> None:
    result = features.compute_speed((0, 0), (3, 4), timestamp_delta_ms=500)

    assert result["speed_px_per_frame"] == pytest.approx(5.0)
    assert result["speed_px_per_second"] == pytest.approx(10.0)


def test_compute_speed_uses_fps_when_timestamp_missing() -> None:
    result = features.compute_speed((0, 0), (3, 4), fps=20)

    assert result["speed_px_per_frame"] == pytest.approx(5.0)
    assert result["speed_px_per_second"] == pytest.approx(100.0)


def test_compute_speed_handles_zero_time_delta() -> None:
    result = features.compute_speed((0, 0), (3, 4), timestamp_delta_ms=0)

    assert result["speed_px_per_frame"] == pytest.approx(5.0)
    assert result["speed_px_per_second"] is None


def test_compute_speed_accepts_dict_points() -> None:
    xy_result = features.compute_speed({"x": 0, "y": 0}, {"x": 3, "y": 4})
    center_result = features.compute_speed(
        {"center_x": 0, "center_y": 0},
        {"center_x": 3, "center_y": 4},
    )
    nested_center_result = features.compute_speed(
        {"center": [0, 0]},
        {"center": [3, 4]},
    )

    assert xy_result["speed_px_per_frame"] == pytest.approx(5.0)
    assert center_result["speed_px_per_frame"] == pytest.approx(5.0)
    assert nested_center_result["speed_px_per_frame"] == pytest.approx(5.0)


def test_compute_direction_vector_from_two_points() -> None:
    assert features.compute_direction_vector([(0, 0), (3, 4)]) == (3.0, 4.0)


def test_compute_direction_vector_with_window() -> None:
    points = [(0, 0), (10, 0), (13, 4)]

    assert features.compute_direction_vector(points, window_size=2) == (3.0, 4.0)
    assert features.compute_direction_vector(points, window_size=3) == (13.0, 4.0)


def test_compute_direction_vector_requires_enough_points() -> None:
    assert features.compute_direction_vector([]) is None
    assert features.compute_direction_vector([(0, 0)]) is None


def test_compute_direction_vector_rejects_invalid_window_size() -> None:
    with pytest.raises(ValueError, match="window_size"):
        features.compute_direction_vector([(0, 0), (1, 1)], window_size=1)


def test_compute_moving_angle_cardinal_direction() -> None:
    assert features.compute_moving_angle([(0, 0), (1, 0)]) == pytest.approx(0.0)
    assert features.compute_moving_angle([(0, 0), (0, 1)]) == pytest.approx(90.0)
    assert features.compute_moving_angle([(0, 0), (-1, 0)]) == pytest.approx(180.0)
    assert features.compute_moving_angle([(0, 0), (0, -1)]) == pytest.approx(270.0)


def test_compute_moving_angle_none_for_zero_vector() -> None:
    assert features.compute_moving_angle([(1, 1), (1, 1)]) is None


def test_compute_moving_angle_none_for_insufficient_points() -> None:
    assert features.compute_moving_angle([]) is None
    assert features.compute_moving_angle([(0, 0)]) is None


def test_compute_dwell_time_for_stationary_points_with_timestamps() -> None:
    points = [
        {"x": 0.0, "y": 0.0, "timestamp_ms": 1000},
        {"x": 0.2, "y": 0.0, "timestamp_ms": 1300},
        {"x": 0.3, "y": 0.0, "timestamp_ms": 1800},
    ]

    assert features.compute_dwell_time(points, speed_threshold=0.5) == 800


def test_compute_dwell_time_zero_for_moving_points() -> None:
    points = [
        {"x": 0.0, "y": 0.0, "timestamp_ms": 1000},
        {"x": 10.0, "y": 0.0, "timestamp_ms": 1500},
    ]

    assert features.compute_dwell_time(points, speed_threshold=1.0) == 0


def test_compute_dwell_time_uses_fps_when_timestamp_missing() -> None:
    points = [(0.0, 0.0), (0.2, 0.0), (0.4, 0.0)]

    assert features.compute_dwell_time(points, speed_threshold=0.5, fps=10) == 200


def test_compute_dwell_time_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError, match="speed_threshold"):
        features.compute_dwell_time([(0, 0), (1, 1)], speed_threshold=-1)


def test_extract_invalid_point_rejected_via_public_functions() -> None:
    with pytest.raises(ValueError, match="point"):
        features.compute_speed((0, 0), {"bad": 1})
    with pytest.raises(ValueError, match="point"):
        features.compute_direction_vector([(0, 0), {"center": [1]}])
