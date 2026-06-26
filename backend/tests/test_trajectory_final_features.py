import pytest

from app.trajectory.engine import TrajectoryEngine


def test_trajectory_engine_outputs_zone_history_lane_relation_and_line_crossings() -> None:
    engine = TrajectoryEngine(fps=10, direction_window=3)

    engine.update(
        _frame(
            1,
            [_track(bbox=[40, 20, 60, 40], center=[50, 30], class_name="car")],
            timestamp_ms=0,
        ),
        zones=_zones(),
    )
    crossed = engine.update(
        _frame(
            2,
            [_track(bbox=[40, 40, 60, 60], center=[50, 50], class_name="car")],
            timestamp_ms=100,
        ),
        zones=_zones(),
    )["trajectory_points"][0]
    settled = engine.update(
        _frame(
            3,
            [_track(bbox=[41, 40, 61, 60], center=[51, 50], class_name="car")],
            timestamp_ms=200,
        ),
        zones=_zones(),
    )["trajectory_points"][0]

    assert crossed["zone_ids"] == [
        "lane-1",
        "parking-1",
        "danger-1",
    ]
    lane_history = _zone_history(crossed, "lane-1")
    assert lane_history["zone_type"] == "vehicle_lane"
    assert lane_history["first_seen_frame"] == 1
    assert lane_history["last_seen_frame"] == 2
    assert lane_history["inside_frames"] == 2
    assert lane_history["inside_duration_ms"] == 100
    assert crossed["lane_relation"]["current_vehicle_lane_ids"] == ["lane-1"]
    assert crossed["lane_relation"]["vehicle_in_no_parking_zone"] is True
    assert crossed["lane_relation"]["object_in_danger_zone"] is True
    assert crossed["line_crossings"] == [
        {
            "line_id": "count-line-1",
            "zone_id": "count-line-1",
            "line_type": "counting",
            "direction": "positive",
            "frame_index": 2,
            "timestamp_ms": 100,
            "previous_point": [50.0, 40.0],
            "current_point": [50.0, 60.0],
        }
    ]
    assert settled["line_crossings"] == []
    assert settled["direction_consistency"] == pytest.approx(0.707107)
    assert settled["moving_angle"] == pytest.approx(87.13759477388825)


def test_trajectory_engine_supports_center_and_bottom_center_zone_strategies() -> None:
    engine = TrajectoryEngine()
    zones = [
        {
            "zone_id": "center-zone",
            "zone_type": "roi",
            "point_strategy": "center",
            "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]],
        },
        {
            "zone_id": "bottom-zone",
            "zone_type": "vehicle_lane",
            "point_strategy": "bottom_center",
            "polygon": [[0, 30], [20, 30], [20, 50], [0, 50]],
        },
    ]

    point = engine.update(
        _frame(
            1,
            [_track(bbox=[0, 0, 20, 40], center=[10, 10], class_name="person")],
            timestamp_ms=0,
        ),
        zones=zones,
    )["trajectory_points"][0]

    assert point["zone_ids"] == ["center-zone", "bottom-zone"]
    assert point["lane_relation"]["person_in_vehicle_lane"] is True
    assert point["lane_relation"]["zone_membership"]["center-zone"]["point_type"] == "center"
    assert (
        point["lane_relation"]["zone_membership"]["bottom-zone"]["point_type"]
        == "bottom_center"
    )


def _zone_history(point: dict, zone_id: str) -> dict:
    for entry in point["zone_history"]:
        if entry["zone_id"] == zone_id:
            return entry
    raise AssertionError(f"missing zone history for {zone_id}")


def _frame(frame_index: int, tracks: list[dict], timestamp_ms: int) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "tracks": tracks,
    }


def _track(
    *,
    bbox: list[float],
    center: list[float],
    class_name: str,
) -> dict:
    return {
        "track_id": 1,
        "class_id": 2,
        "class_name": class_name,
        "confidence": 0.9,
        "bbox": bbox,
        "center": center,
        "state": "confirmed",
    }


def _zones() -> list[dict]:
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    return [
        {
            "zone_id": "lane-1",
            "zone_type": "vehicle_lane",
            "polygon": polygon,
            "point_strategy": "bottom_center",
        },
        {
            "zone_id": "parking-1",
            "zone_type": "no_parking_zone",
            "polygon": polygon,
            "point_strategy": "bottom_center",
        },
        {
            "zone_id": "danger-1",
            "zone_type": "danger_zone",
            "polygon": polygon,
            "point_strategy": "bottom_center",
        },
        {
            "zone_id": "count-line-1",
            "zone_type": "counting_zone",
            "line_id": "count-line-1",
            "line_type": "counting",
            "line": [[0, 50], [100, 50]],
            "point_strategy": "bottom_center",
        },
    ]
