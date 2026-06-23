from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_flow_counting_crossing_generates_event() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    engine.update(_frame(bottom_center=[5, -2]), rules=[_rule()], zones=[])
    result = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[5, 2]),
        rules=[_rule()],
        zones=[],
    )

    assert len(result["events"]) == 1
    assert len(result["event_evidence"]) == 1
    assert result["rule_executions"][0]["status"] == "matched"
    event = result["events"][0]
    assert event["event_type"] == "flow_counting"
    assert event["severity"] == "low"
    assert event["track_id"] == 7
    assert event["class_name"] == "car"
    assert event["rule_id"] == "rule_flow_count_1"
    assert event["start_frame"] == 11
    assert event["end_frame"] == 11
    assert event["start_time_ms"] == 1100
    assert event["end_time_ms"] == 1100
    assert event["status"] == "pending"
    evidence = result["event_evidence"][0]
    assert evidence["evidence_type"] == "line_crossing"
    assert evidence["evidence_json"]["crossing_direction"] == "positive"


def test_flow_counting_no_previous_point_no_match() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(_frame(bottom_center=[5, -2]), rules=[_rule()], zones=[])

    assert result["events"] == []
    assert _reason(result) == "previous_point_not_available"


def test_flow_counting_no_crossing_no_match() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    engine.update(_frame(bottom_center=[1, 2]), rules=[_rule()], zones=[])
    result = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[3, 2]),
        rules=[_rule()],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "line_not_crossed"


def test_flow_counting_direction_any() -> None:
    positive = _run_two_frames([5, -2], [5, 2], parameters={"direction": "any"})
    negative = _run_two_frames([5, 2], [5, -2], parameters={"direction": "any"})

    assert positive["events"][0]["event_type"] == "flow_counting"
    assert positive["event_evidence"][0]["evidence_json"]["crossing_direction"] == "positive"
    assert negative["events"][0]["event_type"] == "flow_counting"
    assert negative["event_evidence"][0]["evidence_json"]["crossing_direction"] == "negative"


def test_flow_counting_direction_mismatch() -> None:
    result = _run_two_frames(
        [5, 2],
        [5, -2],
        parameters={"direction": "positive"},
        record_not_matched=True,
    )

    assert result["events"] == []
    assert _reason(result) == "direction_not_matched"


def test_flow_counting_direction_unknown() -> None:
    result = _run_two_frames(
        [5, 0],
        [5, 2],
        parameters={"direction": "any"},
        record_not_matched=True,
    )

    assert result["events"] == []
    assert _reason(result) == "direction_unknown"


def test_flow_counting_count_once_per_track_true() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )
    rule = _rule(parameters={"count_once_per_track": True})

    engine.update(_frame(frame_index=10, bottom_center=[5, -2]), rules=[rule], zones=[])
    first = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[5, 2]),
        rules=[rule],
        zones=[],
    )
    second = engine.update(
        _frame(frame_index=12, timestamp_ms=1200, bottom_center=[5, -2]),
        rules=[rule],
        zones=[],
    )

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _reason(second) == "already_counted"


def test_flow_counting_count_once_per_track_false() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")
    rule = _rule(parameters={"count_once_per_track": False})

    engine.update(_frame(frame_index=10, bottom_center=[5, -2]), rules=[rule], zones=[])
    first = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[5, 2]),
        rules=[rule],
        zones=[],
    )
    second = engine.update(
        _frame(frame_index=12, timestamp_ms=1200, bottom_center=[5, -2]),
        rules=[rule],
        zones=[],
    )

    assert len(first["events"]) == 1
    assert len(second["events"]) == 1
    assert second["event_evidence"][0]["evidence_json"]["crossing_direction"] == "negative"


def test_flow_counting_invalid_line() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[5, -2]),
        rules=[_rule(parameters={"line": [[0, 0]]})],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_line"


def test_flow_counting_unsupported_direction() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[5, -2]),
        rules=[_rule(parameters={"direction": "in"})],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "unsupported_direction"


def test_flow_counting_invalid_point_type() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(bottom_center=[5, -2]),
        rules=[_rule(parameters={"point_type": "centroid"})],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "invalid_point_type"


def test_flow_counting_missing_point_and_bbox() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )

    result = engine.update(
        _frame(include_bbox=False),
        rules=[_rule()],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "point_not_available"


def test_flow_counting_target_classes_filter() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(class_name="dog", bottom_center=[5, -2]),
        rules=[_rule(target_classes=["car", "person"])],
        zones=[],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "target_class_filtered"


def test_flow_counting_min_track_length_filter() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(track_length=1, bottom_center=[5, -2]),
        rules=[_rule(min_track_length=2)],
        zones=[],
    )

    assert result["events"] == []
    assert _execution(result)["status"] == "skipped"
    assert _reason(result) == "min_track_length_not_met"


def test_flow_counting_person_class_counting() -> None:
    result = _run_two_frames(
        [5, -2],
        [5, 2],
        class_name="person",
        target_classes=["car", "person"],
    )

    assert result["events"][0]["class_name"] == "person"
    assert result["events"][0]["event_type"] == "flow_counting"


def test_flow_counting_evidence_fields() -> None:
    result = _run_two_frames([5, -2], [5, 2])

    evidence_json = result["event_evidence"][0]["evidence_json"]
    assert evidence_json == {
        "line_id": "entry_line_1",
        "line": [[0.0, 0.0], [10.0, 0.0]],
        "previous_point": [5.0, -2.0],
        "current_point": [5.0, 2.0],
        "point_type": "bottom_center",
        "crossing_direction": "positive",
        "configured_direction": "any",
        "count_once_per_track": True,
        "track_id": 7,
        "class_name": "car",
        "frame_index": 11,
        "timestamp_ms": 1100,
    }


def test_flow_counting_cooldown_interaction() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )
    rule = _rule(
        cooldown_seconds=5,
        parameters={"count_once_per_track": False},
    )

    engine.update(_frame(frame_index=10, timestamp_ms=1000, bottom_center=[5, -2]), rules=[rule], zones=[])
    first = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[5, 2]),
        rules=[rule],
        zones=[],
    )
    second = engine.update(
        _frame(frame_index=12, timestamp_ms=1200, bottom_center=[5, -2]),
        rules=[rule],
        zones=[],
    )

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _reason(second) == "cooldown"


def test_flow_counting_reset_clears_state() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
    )
    rule = _rule()
    engine.update(_frame(bottom_center=[5, -2]), rules=[rule], zones=[])

    engine.reset()
    result = engine.update(
        _frame(frame_index=11, timestamp_ms=1100, bottom_center=[5, 2]),
        rules=[rule],
        zones=[],
    )

    assert result["events"] == []
    assert _reason(result) == "previous_point_not_available"


def _run_two_frames(
    first_point: list[float],
    second_point: list[float],
    *,
    parameters: dict | None = None,
    record_not_matched: bool = False,
    class_name: str = "car",
    target_classes: list[str] | tuple[str, ...] = (),
) -> dict:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=record_not_matched,
    )
    rule = _rule(parameters=parameters or {}, target_classes=target_classes)
    engine.update(
        _frame(class_name=class_name, bottom_center=first_point),
        rules=[rule],
        zones=[],
    )
    return engine.update(
        _frame(
            frame_index=11,
            timestamp_ms=1100,
            class_name=class_name,
            bottom_center=second_point,
        ),
        rules=[rule],
        zones=[],
    )


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_flow_count_1",
        "name": "Flow Counting",
        "event_type": "flow_counting",
        "severity": "low",
        "target_classes": (),
        "zone_id": None,
        "parameters": {
            "line_id": "entry_line_1",
            "line": [[0, 0], [10, 0]],
            "direction": "any",
            "point_type": "bottom_center",
            "count_once_per_track": True,
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
        trajectory_point["bbox"] = [0, 0, 10, 10]
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
