from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_illegal_parking_matches_vehicle_stopped_in_no_parking_zone() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    assert len(result["event_evidence"]) == 1
    assert result["rule_executions"][0]["status"] == "matched"
    event = result["events"][0]
    assert event["event_type"] == "illegal_parking"
    assert event["severity"] == "medium"
    assert event["track_id"] == 7
    assert event["class_name"] == "car"
    assert event["zone_id"] == "no_parking_zone_1"
    assert event["rule_id"] == "rule_illegal_parking_1"
    assert event["start_frame"] == 10
    assert event["end_frame"] == 10
    assert event["start_time_ms"] == 1000
    assert event["end_time_ms"] == 1000
    assert event["status"] == "pending"
    assert _execution(result)["output_result"]["reason"] == "vehicle_stopped_in_no_parking_zone"


def test_illegal_parking_no_match_outside_zone() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[150, 150]),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert _execution(result)["status"] == "not_matched"
    assert _reason(result) == "outside_parking_zone"
    assert _execution(result)["output_result"]["inside"] is False


def test_illegal_parking_requires_vehicle_class() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(class_name="person", bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "class_not_vehicle"
    assert _execution(result)["output_result"]["class_name"] == "person"


def test_illegal_parking_speed_above_threshold_no_match() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], speed_px_per_frame=2.0),
        rules=[_rule(parameters={"stop_speed_threshold": 1.0})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "speed_above_threshold"
    assert _execution(result)["output_result"]["speed_px_per_frame"] == 2.0


def test_illegal_parking_dwell_time_not_enough_no_match() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50], dwell_time_ms=2000),
        rules=[_rule(parameters={"min_dwell_time_ms": 3000})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "dwell_time_not_enough"
    assert _execution(result)["output_result"]["dwell_time_ms"] == 2000


def test_illegal_parking_uses_center_when_configured() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(center=[50, 50], bottom_center=[150, 150]),
        rules=[_rule(parameters={"point_type": "center"})],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    evidence_json = result["event_evidence"][0]["evidence_json"]
    assert evidence_json["point_type"] == "center"
    assert evidence_json["point"] == [50.0, 50.0]


def test_illegal_parking_skips_missing_zone() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule(zone_id="missing_zone")],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_not_found"


def test_illegal_parking_skips_disabled_zone() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone(enabled=False)],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_disabled"


def test_illegal_parking_skips_non_supported_zone_type() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone(zone_type="vehicle_lane")],
    )

    assert result["events"] == []
    assert _reason(result) == "zone_type_not_supported"


def test_illegal_parking_respects_target_classes() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(class_name="car", bottom_center=[50, 50]),
        rules=[_rule(target_classes=["person"])],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "target_class_filtered"


def test_illegal_parking_respects_min_track_length() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(track_length=1, bottom_center=[50, 50]),
        rules=[_rule(min_track_length=3)],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "min_track_length_not_met"


def test_illegal_parking_builds_evidence() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone(polygon=polygon)],
    )

    evidence = result["event_evidence"][0]
    assert evidence["evidence_type"] == "dwell"
    assert evidence["track_id"] == 7
    assert evidence["frame_index"] == 10
    assert evidence["timestamp_ms"] == 1000
    assert evidence["evidence_json"] == {
        "zone_id": "no_parking_zone_1",
        "zone_type": "no_parking_zone",
        "point": [50.0, 50.0],
        "point_type": "bottom_center",
        "inside": True,
        "class_name": "car",
        "speed_px_per_frame": 0.5,
        "speed_px_per_second": 5.0,
        "stop_speed_threshold": 1.0,
        "dwell_time_ms": 3000,
        "min_dwell_time_ms": 3000,
        "track_length": 3,
        "polygon": polygon,
    }


def test_illegal_parking_cooldown_prevents_duplicate_event() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    rule = _rule(cooldown_seconds=5)

    first = engine.update(
        _frame(frame_index=10, timestamp_ms=1000, bottom_center=[50, 50]),
        rules=[rule],
        zones=[_zone()],
    )
    second = engine.update(
        _frame(frame_index=11, timestamp_ms=3000, bottom_center=[50, 50]),
        rules=[rule],
        zones=[_zone()],
    )

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _execution(second)["status"] == "skipped"
    assert _reason(second) == "cooldown"


def test_illegal_parking_invalid_point_type() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule(parameters={"point_type": "centroid"})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_point_type"


def test_illegal_parking_missing_point_and_bbox() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(include_bbox=False),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "point_not_available"


def test_illegal_parking_max_center_shift_not_supported_if_set() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule(parameters={"max_center_shift": 2.0})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "max_center_shift_not_supported"


def test_illegal_parking_allows_vehicle_lane_when_configured() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule(parameters={"zone_types": ["no_parking_zone", "vehicle_lane"]})],
        zones=[_zone(zone_type="vehicle_lane")],
    )

    assert len(result["events"]) == 1
    assert result["event_evidence"][0]["evidence_json"]["zone_type"] == "vehicle_lane"


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_illegal_parking_1",
        "name": "Illegal Parking",
        "event_type": "illegal_parking",
        "severity": "medium",
        "target_classes": (),
        "zone_id": "no_parking_zone_1",
        "parameters": {},
        "cooldown_seconds": 0,
        "min_track_length": 1,
    }
    values.update(overrides)
    return EventRule(**values)


def _zone(**overrides) -> dict:
    values = {
        "zone_id": "no_parking_zone_1",
        "name": "No Parking Area",
        "zone_type": "no_parking_zone",
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
    track_length: int = 3,
    center: list[float] | None = None,
    bottom_center: list[float] | None = None,
    bbox: list[float] | None = None,
    include_bbox: bool = True,
    speed_px_per_frame: float = 0.5,
    speed_px_per_second: float | None = 5.0,
    dwell_time_ms: int = 3000,
) -> dict:
    trajectory_point = {
        "track_id": track_id,
        "class_name": class_name,
        "track_length": track_length,
        "speed_px_per_frame": speed_px_per_frame,
        "speed_px_per_second": speed_px_per_second,
        "dwell_time_ms": dwell_time_ms,
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
