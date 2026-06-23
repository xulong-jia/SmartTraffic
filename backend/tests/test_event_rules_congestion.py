from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_congestion_matches_when_vehicle_count_and_low_speed_thresholds_met() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(
            [
                _point(track_id=7, bottom_center=[20, 20], speed_px_per_frame=1.0),
                _point(track_id=8, bottom_center=[30, 30], speed_px_per_frame=1.5),
                _point(track_id=9, bottom_center=[40, 40], speed_px_per_frame=2.0),
            ]
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 3, "avg_speed_threshold": 2.0})],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    assert len(result["event_evidence"]) == 1
    assert result["rule_executions"][0]["status"] == "matched"
    event = result["events"][0]
    assert event["event_type"] == "congestion"
    assert event["severity"] == "medium"
    assert event["track_id"] is None
    assert event["class_name"] is None
    assert event["zone_id"] == "lane_zone_1"
    assert event["rule_id"] == "rule_congestion_1"
    assert event["start_frame"] == 10
    assert event["end_frame"] == 10
    assert event["start_time_ms"] == 1000
    assert event["end_time_ms"] == 1000
    assert event["status"] == "pending"
    assert result["event_evidence"][0]["evidence_type"] == "zone_statistics"


def test_congestion_vehicle_count_below_threshold_no_match() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame(
            [
                _point(track_id=7, bottom_center=[20, 20], speed_px_per_frame=1.0),
                _point(track_id=8, bottom_center=[30, 30], speed_px_per_frame=1.0),
            ]
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 3})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "vehicle_count_below_threshold"


def test_congestion_avg_speed_above_threshold_no_match() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame(
            [
                _point(track_id=7, bottom_center=[20, 20], speed_px_per_frame=4.0),
                _point(track_id=8, bottom_center=[30, 30], speed_px_per_frame=5.0),
            ]
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 2, "avg_speed_threshold": 2.0})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "avg_speed_above_threshold"
    assert _execution(result)["output_result"]["avg_speed_px_per_frame"] == 4.5


def test_congestion_ignores_non_vehicle_classes() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame(
            [
                _point(track_id=7, class_name="car", bottom_center=[20, 20]),
                _point(track_id=8, class_name="person", bottom_center=[30, 30]),
                _point(track_id=9, class_name="bicycle", bottom_center=[40, 40]),
            ]
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 2})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "vehicle_count_below_threshold"
    assert _execution(result)["output_result"]["vehicle_count"] == 1


def test_congestion_skips_missing_zone() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame([_point(track_id=7, bottom_center=[20, 20])]),
        rules=[_rule(zone_id="missing_zone")],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_not_found"


def test_congestion_skips_disabled_zone() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame([_point(track_id=7, bottom_center=[20, 20])]),
        rules=[_rule()],
        zones=[_zone(enabled=False)],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_disabled"


def test_congestion_skips_non_supported_zone_type() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame([_point(track_id=7, bottom_center=[20, 20])]),
        rules=[_rule()],
        zones=[_zone(zone_type="danger_zone")],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_type_not_supported"


def test_congestion_invalid_polygon() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame([_point(track_id=7, bottom_center=[20, 20])]),
        rules=[_rule()],
        zones=[_zone(polygon=[[0, 0], [100, 0]])],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_zone_polygon"


def test_congestion_ignores_points_outside_zone() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame(
            [
                _point(track_id=7, bottom_center=[20, 20]),
                _point(track_id=8, bottom_center=[150, 150]),
            ]
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 2})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "vehicle_count_below_threshold"
    assert _execution(result)["output_result"]["vehicle_count"] == 1


def test_congestion_min_congestion_frames() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)
    rule = _rule(parameters={"vehicle_count_threshold": 2, "min_congestion_frames": 3})

    first = engine.update(_frame(_congested_points(), frame_index=10), rules=[rule], zones=[_zone()])
    second = engine.update(_frame(_congested_points(), frame_index=11), rules=[rule], zones=[_zone()])
    third = engine.update(_frame(_congested_points(), frame_index=12), rules=[rule], zones=[_zone()])

    assert first["events"] == []
    assert _reason(first) == "congestion_frames_not_enough"
    assert second["events"] == []
    assert _reason(second) == "congestion_frames_not_enough"
    assert len(third["events"]) == 1
    assert third["events"][0]["start_frame"] == 10
    assert third["events"][0]["end_frame"] == 12
    assert third["event_evidence"][0]["evidence_json"]["congestion_frame_count"] == 3


def test_congestion_builds_zone_statistics_evidence() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    result = engine.update(
        _frame(
            [
                _point(track_id=7, class_name="car", bottom_center=[20, 20], speed_px_per_frame=1.0),
                _point(track_id=8, class_name="bus", bottom_center=[30, 30], speed_px_per_frame=2.0),
                _point(track_id=9, class_name="truck", bottom_center=[40, 40], speed_px_per_frame=1.5),
            ],
            frame_index=22,
            timestamp_ms=2200,
        ),
        rules=[_rule(parameters={"vehicle_count_threshold": 3, "avg_speed_threshold": 2.0})],
        zones=[_zone(polygon=polygon)],
    )

    evidence = result["event_evidence"][0]
    assert evidence["track_id"] is None
    assert evidence["frame_index"] == 22
    assert evidence["timestamp_ms"] == 2200
    assert evidence["evidence_json"] == {
        "zone_id": "lane_zone_1",
        "zone_type": "vehicle_lane",
        "frame_index": 22,
        "timestamp_ms": 2200,
        "vehicle_count": 3,
        "vehicle_count_threshold": 3,
        "avg_speed_px_per_frame": 1.5,
        "avg_speed_threshold": 2.0,
        "track_ids": [7, 8, 9],
        "class_counts": {"bus": 1, "car": 1, "truck": 1},
        "min_congestion_frames": 1,
        "congestion_frame_count": 1,
        "polygon": polygon,
    }


def test_congestion_cooldown_prevents_duplicate_event() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    rule = _rule(
        cooldown_seconds=5,
        parameters={"vehicle_count_threshold": 2, "min_congestion_frames": 1},
    )

    first = engine.update(
        _frame(_congested_points(), frame_index=10, timestamp_ms=1000),
        rules=[rule],
        zones=[_zone()],
    )
    second = engine.update(
        _frame(_congested_points(), frame_index=11, timestamp_ms=2000),
        rules=[rule],
        zones=[_zone()],
    )

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _execution(second)["status"] == "skipped"
    assert _reason(second) == "cooldown"


def test_congestion_reset_clears_state() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)
    rule = _rule(parameters={"vehicle_count_threshold": 2, "min_congestion_frames": 2})
    engine.update(_frame(_congested_points(), frame_index=10), rules=[rule], zones=[_zone()])

    engine.reset()
    result = engine.update(_frame(_congested_points(), frame_index=11), rules=[rule], zones=[_zone()])

    assert result["events"] == []
    assert _reason(result) == "congestion_frames_not_enough"
    assert _execution(result)["output_result"]["congestion_frame_count"] == 1


def test_congestion_uses_center_when_configured() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(
            [
                _point(track_id=7, center=[20, 20], bottom_center=[150, 150]),
                _point(track_id=8, center=[30, 30], bottom_center=[150, 150]),
            ]
        ),
        rules=[
            _rule(
                parameters={
                    "point_type": "center",
                    "vehicle_count_threshold": 2,
                    "avg_speed_threshold": 2.0,
                }
            )
        ],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    assert result["event_evidence"][0]["evidence_json"]["track_ids"] == [7, 8]


def test_congestion_min_track_length_filter_inside_callback() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame(
            [
                _point(track_id=7, bottom_center=[20, 20], track_length=1),
                _point(track_id=8, bottom_center=[30, 30], track_length=3),
            ]
        ),
        rules=[_rule(min_track_length=2, parameters={"vehicle_count_threshold": 2})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "vehicle_count_below_threshold"
    assert _execution(result)["output_result"]["vehicle_count"] == 1


def test_congestion_no_trajectory_points() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        {"frame_index": 10, "timestamp_ms": 1000, "trajectory_points": []},
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "no_trajectory_points"


def test_congestion_not_aggregate_rule() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)

    result = engine.update(
        _frame([_point(track_id=7, bottom_center=[20, 20])]),
        rules=[_rule(parameters={"rule_mode": "track"})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "not_aggregate_rule"


def test_congestion_frame_already_evaluated() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001", record_not_matched=True)
    rule = _rule(parameters={"vehicle_count_threshold": 2, "min_congestion_frames": 3})
    frame = _frame(_congested_points(), frame_index=10)

    first = engine.update(frame, rules=[rule], zones=[_zone()])
    second = engine.update(frame, rules=[rule], zones=[_zone()])

    assert first["events"] == []
    assert _reason(first) == "congestion_frames_not_enough"
    assert second["events"] == []
    assert _reason(second) == "frame_already_evaluated"
    assert _execution(second)["output_result"]["congestion_frame_count"] == 1


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_congestion_1",
        "name": "Congestion Detection",
        "event_type": "congestion",
        "severity": "medium",
        "target_classes": ("car", "truck", "bus", "motorcycle"),
        "zone_id": "lane_zone_1",
        "parameters": {
            "rule_mode": "aggregate",
            "zone_types": ["vehicle_lane", "roi"],
            "point_type": "bottom_center",
            "vehicle_count_threshold": 2,
            "avg_speed_threshold": 2.0,
            "min_congestion_frames": 1,
        },
        "cooldown_seconds": 0,
        "min_track_length": 2,
    }
    if "parameters" in overrides:
        values["parameters"] = {
            **values["parameters"],
            **overrides.pop("parameters"),
        }
    values.update(overrides)
    return EventRule(**values)


def _zone(**overrides) -> dict:
    values = {
        "zone_id": "lane_zone_1",
        "name": "Lane Zone",
        "zone_type": "vehicle_lane",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "enabled": True,
    }
    values.update(overrides)
    return values


def _frame(
    trajectory_points: list[dict],
    *,
    frame_index: int = 10,
    timestamp_ms: int | None = 1000,
) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "trajectory_points": trajectory_points,
    }


def _point(
    *,
    track_id: int,
    class_name: str = "car",
    track_length: int = 3,
    speed_px_per_frame: float = 1.0,
    center: list[float] | None = None,
    bottom_center: list[float] | None = None,
    bbox: list[float] | None = None,
    include_bbox: bool = True,
) -> dict:
    trajectory_point = {
        "track_id": track_id,
        "class_name": class_name,
        "track_length": track_length,
        "speed_px_per_frame": speed_px_per_frame,
    }
    if center is not None:
        trajectory_point["center"] = center
    if bottom_center is not None:
        trajectory_point["bottom_center"] = bottom_center
    if bbox is not None:
        trajectory_point["bbox"] = bbox
    elif include_bbox:
        trajectory_point["bbox"] = [10, 10, 30, 30]
    return trajectory_point


def _congested_points() -> list[dict]:
    return [
        _point(track_id=7, bottom_center=[20, 20], speed_px_per_frame=1.0),
        _point(track_id=8, bottom_center=[30, 30], speed_px_per_frame=1.5),
    ]


def _execution(result: dict) -> dict:
    assert result["rule_executions"]
    return result["rule_executions"][0]


def _reason(result: dict) -> str:
    return _execution(result)["output_result"]["reason"]
