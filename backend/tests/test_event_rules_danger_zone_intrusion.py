from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_danger_zone_intrusion_matches_bottom_center_inside() -> None:
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
    assert event["event_type"] == "danger_zone_intrusion"
    assert event["severity"] == "high"
    assert event["track_id"] == 7
    assert event["class_name"] == "car"
    assert event["zone_id"] == "danger_zone_1"
    assert event["rule_id"] == "rule_danger_zone_1"
    assert event["start_frame"] == 10
    assert event["end_frame"] == 10
    assert event["start_time_ms"] == 1000
    assert event["end_time_ms"] == 1000
    assert event["status"] == "pending"


def test_danger_zone_intrusion_no_match_outside() -> None:
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
    assert _reason(result) == "outside_danger_zone"
    assert _execution(result)["output_result"]["inside"] is False


def test_danger_zone_intrusion_uses_center_when_configured() -> None:
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


def test_danger_zone_intrusion_skips_missing_zone() -> None:
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


def test_danger_zone_intrusion_skips_disabled_zone() -> None:
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


def test_danger_zone_intrusion_skips_non_danger_zone() -> None:
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


def test_danger_zone_intrusion_respects_target_classes() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(class_name="dog", bottom_center=[50, 50]),
        rules=[_rule(target_classes=["person", "car"])],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "target_class_filtered"


def test_danger_zone_intrusion_respects_min_track_length() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(track_length=1, bottom_center=[50, 50]),
        rules=[_rule(min_track_length=3)],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "min_track_length_not_met"


def test_danger_zone_intrusion_builds_zone_evidence() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone(polygon=polygon)],
    )

    evidence = result["event_evidence"][0]
    assert evidence["evidence_type"] == "zone"
    assert evidence["track_id"] == 7
    assert evidence["frame_index"] == 10
    assert evidence["timestamp_ms"] == 1000
    assert evidence["evidence_json"] == {
        "zone_id": "danger_zone_1",
        "zone_type": "danger_zone",
        "point": [50.0, 50.0],
        "point_type": "bottom_center",
        "inside": True,
        "polygon": polygon,
    }


def test_danger_zone_intrusion_cooldown_prevents_duplicate_event() -> None:
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


def test_danger_zone_intrusion_invalid_point_type() -> None:
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


def test_danger_zone_intrusion_missing_point_and_bbox() -> None:
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


def test_danger_zone_intrusion_min_inside_frames_not_supported() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule(parameters={"min_inside_frames": 2})],
        zones=[_zone()],
    )

    assert result["events"] == []
    assert _reason(result) == "min_inside_frames_not_supported"


def test_danger_zone_intrusion_invalid_zone_polygon() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[50, 50]),
        rules=[_rule()],
        zones=[_zone(polygon=[[0, 0], [100, 0]])],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_zone_polygon"


def test_danger_zone_intrusion_falls_back_to_bbox_bottom_center() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(bbox=[40, 20, 60, 50]),
        rules=[_rule()],
        zones=[_zone()],
    )

    assert len(result["events"]) == 1
    assert result["event_evidence"][0]["evidence_json"]["point"] == [50.0, 50.0]


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_danger_zone_1",
        "name": "Danger Zone Intrusion",
        "event_type": "danger_zone_intrusion",
        "severity": "high",
        "target_classes": (),
        "zone_id": "danger_zone_1",
        "parameters": {},
        "cooldown_seconds": 0,
        "min_track_length": 1,
    }
    values.update(overrides)
    return EventRule(**values)


def _zone(**overrides) -> dict:
    values = {
        "zone_id": "danger_zone_1",
        "name": "Loading Area",
        "zone_type": "danger_zone",
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
) -> dict:
    trajectory_point = {
        "track_id": track_id,
        "class_name": class_name,
        "track_length": track_length,
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
