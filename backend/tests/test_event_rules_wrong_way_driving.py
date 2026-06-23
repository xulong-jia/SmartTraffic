from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_wrong_way_driving_matches_vehicle_wrong_direction_in_lane() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    assert len(result["event_evidence"]) == 1
    assert result["rule_executions"][0]["status"] == "matched"
    event = result["events"][0]
    assert event["event_type"] == "wrong_way_driving"
    assert event["severity"] == "high"
    assert event["track_id"] == 7
    assert event["class_name"] == "car"
    assert event["zone_id"] == "vehicle_lane_1"
    assert event["rule_id"] == "rule_wrong_way_1"
    assert event["start_frame"] == 10
    assert event["end_frame"] == 10
    assert event["start_time_ms"] == 1000
    assert event["end_time_ms"] == 1000
    assert event["status"] == "pending"
    assert _reason(result) == "wrong_way_direction_detected"


def test_wrong_way_driving_no_match_direction_allowed() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=100.0),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert _execution(result)["status"] == "not_matched"
    assert _reason(result) == "direction_allowed"
    assert _execution(result)["output_result"]["angle_difference"] == 10.0


def test_wrong_way_driving_requires_vehicle_class() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(class_name="person", bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "class_not_vehicle"
    assert _execution(result)["output_result"]["class_name"] == "person"


def test_wrong_way_driving_no_match_outside_lane() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[150, 150], moving_angle=270.0),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "outside_lane_zone"
    assert _execution(result)["output_result"]["inside"] is False


def test_wrong_way_driving_uses_center_when_configured() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(center=[50, 50], bottom_center=[150, 150], moving_angle=270.0),
        rules=[_rule(parameters={"point_type": "center"})],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    evidence_json = result["event_evidence"][0]["evidence_json"]
    assert evidence_json["point_type"] == "center"
    assert evidence_json["point"] == [50.0, 50.0]


def test_wrong_way_driving_skips_missing_zone() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule(zone_id="missing_zone")],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_not_found"


def test_wrong_way_driving_skips_disabled_zone() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule()],
        zones=[_zone(enabled=False)],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_disabled"


def test_wrong_way_driving_skips_non_supported_zone_type() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule()],
        zones=[_zone(zone_type="danger_zone")],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_type_not_supported"


def test_wrong_way_driving_respects_target_classes() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(class_name="car", bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule(target_classes=["person"])],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "target_class_filtered"


def test_wrong_way_driving_respects_min_track_length() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(track_length=1, bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule(min_track_length=5)],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "min_track_length_not_met"


def test_wrong_way_driving_speed_below_threshold_no_match() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0, speed_px_per_frame=0.5),
        rules=[_rule(parameters={"min_speed_px_per_frame": 1.0})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "speed_below_threshold"
    assert _execution(result)["output_result"]["speed_px_per_frame"] == 0.5


def test_wrong_way_driving_missing_moving_angle() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=None),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "moving_angle_not_available"


def test_wrong_way_driving_invalid_point_type() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule(parameters={"point_type": "centroid"})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_point_type"


def test_wrong_way_driving_builds_direction_evidence() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    result = engine.update(
        _frame(
            bottom_center=[50, 50],
            moving_angle=270.0,
            direction_vector=[0.0, -1.0],
        ),
        rules=[_rule()],
        zones=[_zone(polygon=polygon)],
    )

    evidence = result["event_evidence"][0]
    assert evidence["evidence_type"] == "direction"
    assert evidence["track_id"] == 7
    assert evidence["frame_index"] == 10
    assert evidence["timestamp_ms"] == 1000
    assert evidence["evidence_json"] == {
        "zone_id": "vehicle_lane_1",
        "zone_type": "vehicle_lane",
        "point": [50.0, 50.0],
        "point_type": "bottom_center",
        "inside": True,
        "class_name": "car",
        "moving_angle": 270.0,
        "allowed_angle": 90.0,
        "angle_tolerance": 45.0,
        "angle_difference": 180.0,
        "speed_px_per_frame": 2.0,
        "min_speed_px_per_frame": 1.0,
        "direction_vector": [0.0, -1.0],
        "track_length": 5,
        "polygon": polygon,
    }


def test_wrong_way_driving_cooldown_prevents_duplicate_event() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    rule = _rule(cooldown_seconds=5)

    first = engine.update(
        _frame(frame_index=10, timestamp_ms=1000, bottom_center=[50, 50], moving_angle=270.0),
        rules=[rule],
        zones=[_zone()],
    )
    second = engine.update(
        _frame(frame_index=11, timestamp_ms=3000, bottom_center=[50, 50], moving_angle=270.0),
        rules=[rule],
        zones=[_zone()],
    )

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _execution(second)["status"] == "skipped"
    assert _reason(second) == "cooldown"


def test_wrong_way_driving_min_wrong_way_frames_not_supported() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=270.0),
        rules=[_rule(parameters={"min_wrong_way_frames": 2})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "min_wrong_way_frames_not_supported"


def test_wrong_way_driving_lateral_motion_not_treated_as_wrong_way() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], moving_angle=0.0),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "direction_allowed"
    output = _execution(result)["output_result"]
    assert output["angle_difference"] == 90.0
    assert output["strict_wrong_way_threshold"] == 135.0


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_wrong_way_1",
        "name": "Wrong Way Driving",
        "event_type": "wrong_way_driving",
        "severity": "high",
        "target_classes": (),
        "zone_id": "vehicle_lane_1",
        "parameters": {
            "allowed_angle": 90.0,
            "angle_tolerance": 45.0,
            "min_speed_px_per_frame": 1.0,
        },
        "cooldown_seconds": 0,
        "min_track_length": 1,
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
        "zone_id": "vehicle_lane_1",
        "name": "Vehicle Lane",
        "zone_type": "vehicle_lane",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "enabled": True,
    }
    values.update(overrides)
    return values


def _frame(
    *,
    frame_index: int = 10,
    timestamp_ms: int | None = 1000,
    track_id: int = 7,
    class_name: str = "car",
    track_length: int = 5,
    center: list[float] | None = None,
    bottom_center: list[float] | None = None,
    bbox: list[float] | None = None,
    include_bbox: bool = True,
    speed_px_per_frame: float | None = 2.0,
    speed_px_per_second: float | None = 20.0,
    moving_angle: float | None = 270.0,
    direction_vector: list[float] | None = None,
) -> dict:
    trajectory_point = {
        "track_id": track_id,
        "class_name": class_name,
        "track_length": track_length,
        "speed_px_per_frame": speed_px_per_frame,
        "speed_px_per_second": speed_px_per_second,
        "moving_angle": moving_angle,
        "direction_vector": direction_vector or [0.0, -1.0],
    }
    if center is not None:
        trajectory_point["center"] = center
    if bottom_center is not None:
        trajectory_point["bottom_center"] = bottom_center
    if bbox is not None:
        trajectory_point["bbox"] = bbox
    elif include_bbox:
        trajectory_point["bbox"] = [10, 10, 20, 30]
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "trajectory_points": [trajectory_point],
    }


def _execution(result: dict) -> dict:
    assert result["rule_executions"]
    return result["rule_executions"][0]


def _reason(result: dict) -> str:
    return _execution(result)["output_result"]["reason"]
