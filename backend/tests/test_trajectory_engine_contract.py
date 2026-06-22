import pytest

from app.trajectory.engine import TrajectoryEngine


def _frame(frame_index: int, tracks: list[dict], timestamp_ms: int | None = None) -> dict:
    payload = {"frame_index": frame_index, "tracks": tracks}
    if timestamp_ms is not None:
        payload["timestamp_ms"] = timestamp_ms
    return payload


def _track(
    track_id: int = 1,
    bbox: list[float] | None = None,
    center: list[float] | None = None,
    state: str = "confirmed",
) -> dict:
    payload = {
        "track_id": track_id,
        "class_id": 2,
        "class_name": "car",
        "confidence": 0.88,
        "bbox": bbox or [0.0, 0.0, 10.0, 20.0],
        "state": state,
    }
    if center is not None:
        payload["center"] = center
    return payload


def test_trajectory_engine_empty_tracks() -> None:
    engine = TrajectoryEngine()

    result = engine.update(_frame(1, [], timestamp_ms=100))

    assert result == {"frame_index": 1, "timestamp_ms": 100, "trajectory_points": []}
    assert engine.get_summary() == {
        "total_tracks_seen": 0,
        "active_track_ids": [],
        "total_trajectory_points": 0,
        "track_state_counts": {},
        "max_track_length": 0,
        "avg_track_length": 0.0,
    }


def test_trajectory_engine_single_track_first_point_contract() -> None:
    engine = TrajectoryEngine()

    result = engine.update(
        _frame(
            1,
            [_track(center=[5.0, 10.0])],
            timestamp_ms=100,
        )
    )

    point = result["trajectory_points"][0]
    assert result["frame_index"] == 1
    assert result["timestamp_ms"] == 100
    assert point["track_id"] == 1
    assert point["class_id"] == 2
    assert point["class_name"] == "car"
    assert point["confidence"] == pytest.approx(0.88)
    assert point["bbox"] == [0.0, 0.0, 10.0, 20.0]
    assert point["center"] == [5.0, 10.0]
    assert point["bottom_center"] == [5.0, 20.0]
    assert point["state"] == "confirmed"
    assert point["speed_px_per_frame"] == pytest.approx(0.0)
    assert point["speed_px_per_second"] is None
    assert point["direction_vector"] is None
    assert point["moving_angle"] is None
    assert point["dwell_time_ms"] == 0
    assert point["zone_ids"] == []
    assert point["zone_history"] == []
    assert point["lane_relation"] == {}
    assert point["line_crossings"] == []
    assert point["track_length"] == 1
    assert point["last_seen_frame"] == 1
    assert point["last_seen_timestamp_ms"] == 100


def test_trajectory_engine_single_track_two_frames_speed_and_direction() -> None:
    engine = TrajectoryEngine(fps=10)
    engine.update(_frame(1, [_track(center=[0.0, 0.0])], timestamp_ms=0))

    result = engine.update(
        _frame(
            2,
            [_track(bbox=[2.0, 3.0, 4.0, 5.0], center=[3.0, 4.0])],
            timestamp_ms=100,
        )
    )

    point = result["trajectory_points"][0]
    assert point["speed_px_per_frame"] == pytest.approx(5.0)
    assert point["speed_px_per_second"] == pytest.approx(50.0)
    assert point["direction_vector"] == [3.0, 4.0]
    assert point["moving_angle"] == pytest.approx(53.13010235415598)
    assert point["track_length"] == 2
    assert point["dwell_time_ms"] == 0


def test_trajectory_engine_multiple_tracks() -> None:
    engine = TrajectoryEngine()

    result = engine.update(
        _frame(
            1,
            [
                _track(track_id=1, center=[5.0, 10.0]),
                _track(track_id=2, bbox=[20.0, 10.0, 30.0, 30.0], center=[25.0, 20.0]),
            ],
            timestamp_ms=100,
        )
    )

    assert [point["track_id"] for point in result["trajectory_points"]] == [1, 2]
    assert engine.get_track_state(1)["points"] == [
        {"x": 5.0, "y": 10.0, "frame_index": 1, "timestamp_ms": 100}
    ]
    assert engine.get_track_state(2)["points"] == [
        {"x": 25.0, "y": 20.0, "frame_index": 1, "timestamp_ms": 100}
    ]


def test_trajectory_engine_reset() -> None:
    engine = TrajectoryEngine()
    engine.update(_frame(1, [_track(center=[5.0, 10.0])], timestamp_ms=100))

    engine.reset()

    assert engine.get_track_state(1) is None
    assert engine.get_summary()["total_tracks_seen"] == 0


def test_trajectory_engine_get_track_state() -> None:
    engine = TrajectoryEngine()
    engine.update(_frame(1, [_track(center=[5.0, 10.0])], timestamp_ms=100))

    state = engine.get_track_state(1)
    assert state is not None
    state["points"].append({"x": 999.0, "y": 999.0, "frame_index": 9, "timestamp_ms": 9})

    assert len(engine.get_track_state(1)["points"]) == 1


def test_trajectory_engine_summary() -> None:
    engine = TrajectoryEngine()
    engine.update(_frame(1, [_track(track_id=1, center=[0.0, 0.0])], timestamp_ms=0))
    engine.update(
        _frame(
            2,
            [
                _track(track_id=1, center=[1.0, 0.0]),
                _track(track_id=2, center=[10.0, 0.0]),
            ],
            timestamp_ms=100,
        )
    )

    assert engine.get_summary() == {
        "total_tracks_seen": 2,
        "active_track_ids": [1, 2],
        "total_trajectory_points": 3,
        "track_state_counts": {"confirmed": 2},
        "max_track_length": 2,
        "avg_track_length": 1.5,
    }


def test_trajectory_engine_handles_missing_optional_timestamp() -> None:
    engine = TrajectoryEngine()

    result = engine.update(_frame(1, [_track(center=[5.0, 10.0])]))

    point = result["trajectory_points"][0]
    assert result["timestamp_ms"] is None
    assert point["last_seen_timestamp_ms"] is None


def test_trajectory_engine_rejects_missing_track_id() -> None:
    engine = TrajectoryEngine()
    track = _track(center=[5.0, 10.0])
    del track["track_id"]

    with pytest.raises(ValueError, match="track_id"):
        engine.update(_frame(1, [track]))


def test_trajectory_engine_rejects_invalid_bbox() -> None:
    engine = TrajectoryEngine()

    with pytest.raises(ValueError, match="bbox"):
        engine.update(_frame(1, [_track(bbox=[0.0, 1.0, 2.0])]))


def test_trajectory_engine_center_fallback_from_bbox() -> None:
    engine = TrajectoryEngine()

    result = engine.update(_frame(1, [_track()], timestamp_ms=100))

    assert result["trajectory_points"][0]["center"] == [5.0, 10.0]


def test_trajectory_engine_does_not_output_tentative_by_default() -> None:
    engine = TrajectoryEngine()

    result = engine.update(
        _frame(1, [_track(center=[5.0, 10.0], state="tentative")], timestamp_ms=100)
    )

    assert result["trajectory_points"] == []
    assert engine.get_track_state(1)["state"] == "tentative"
    assert engine.get_track_state(1)["points"] == []


def test_trajectory_engine_does_not_output_lost_by_default() -> None:
    engine = TrajectoryEngine()
    engine.update(_frame(1, [_track(center=[5.0, 10.0])], timestamp_ms=100))

    result = engine.update(
        _frame(2, [_track(center=[6.0, 10.0], state="lost")], timestamp_ms=200)
    )

    assert result["trajectory_points"] == []
    assert engine.get_track_state(1)["state"] == "lost"
    assert engine.get_track_state(1)["points"] == [
        {"x": 5.0, "y": 10.0, "frame_index": 1, "timestamp_ms": 100}
    ]
