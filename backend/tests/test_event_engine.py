import pytest

from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_event_engine_empty_rules() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(_frame(), rules=[])

    assert result == {
        "frame_index": 10,
        "timestamp_ms": 1000,
        "events": [],
        "event_evidence": [],
        "rule_executions": [],
    }


def test_event_engine_empty_trajectory_points() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        {"frame_index": 10, "timestamp_ms": 1000, "trajectory_points": []},
        rules=[_rule()],
    )

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert result["rule_executions"] == []


def test_event_engine_calls_matching_rule() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    assert len(result["events"]) == 1
    assert len(result["event_evidence"]) == 1
    assert len(result["rule_executions"]) == 1
    event = result["events"][0]
    evidence = result["event_evidence"][0]
    execution = result["rule_executions"][0]
    assert event["event_type"] == "danger_zone_intrusion"
    assert event["severity"] == "high"
    assert event["track_id"] == 7
    assert event["class_name"] == "car"
    assert event["zone_id"] == "zone_001"
    assert event["rule_id"] == "rule_001"
    assert event["start_frame"] == 10
    assert event["end_frame"] == 10
    assert event["start_time_ms"] == 1000
    assert event["end_time_ms"] == 1000
    assert evidence["event_id"] == event["event_id"]
    assert evidence["evidence_type"] == "rule"
    assert execution["status"] == "matched"


def test_event_engine_skips_disabled_rule() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(_frame(), rules=[_rule(enabled=False)])

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert _execution_reasons(result) == ["rule_disabled"]


def test_event_engine_filters_target_classes() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(_frame(class_name="person"), rules=[_rule(target_classes=["car"])])

    assert result["events"] == []
    assert _execution_reasons(result) == ["target_class_filtered"]


def test_event_engine_filters_min_track_length() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(_frame(track_length=2), rules=[_rule(min_track_length=3)])

    assert result["events"] == []
    assert _execution_reasons(result) == ["min_track_length_not_met"]


def test_event_engine_generates_rule_execution_for_matched() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    event = result["events"][0]
    execution = result["rule_executions"][0]
    assert execution["rule_id"] == "rule_001"
    assert execution["event_id"] == event["event_id"]
    assert execution["track_id"] == 7
    assert execution["frame_index"] == 10
    assert execution["input_features"]["track_id"] == 7
    assert execution["output_result"]["matched"] is True


def test_event_engine_records_skipped() -> None:
    engine = EventEngine(run_id="run_001", video_id="video_001")

    result = engine.update(
        _frame(),
        rules=[_rule(rule_id="disabled", enabled=False), _rule(rule_id="missing")],
    )

    assert [execution["status"] for execution in result["rule_executions"]] == [
        "skipped",
        "skipped",
    ]
    assert _execution_reasons(result) == ["rule_disabled", "rule_callback_missing"]


def test_event_engine_handles_rule_error() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _error_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert result["rule_executions"][0]["status"] == "error"
    assert result["rule_executions"][0]["output_result"]["reason"] == "rule_error"


def test_event_engine_cooldown() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )
    rule = _rule(cooldown_seconds=10)

    first = engine.update(_frame(timestamp_ms=1000), rules=[rule])
    second = engine.update(_frame(frame_index=11, timestamp_ms=5000), rules=[rule])

    assert len(first["events"]) == 1
    assert second["events"] == []
    assert _execution_reasons(second) == ["cooldown"]


def test_event_engine_reset() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )
    rule = _rule(cooldown_seconds=10)
    engine.update(_frame(timestamp_ms=1000), rules=[rule])

    engine.reset()
    result = engine.update(_frame(frame_index=11, timestamp_ms=5000), rules=[rule])

    assert len(result["events"]) == 1
    assert engine.get_summary()["total_events"] == 1


def test_event_engine_callback_state_persists_during_evaluate() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _stateful_matching_callback},
    )

    result = engine.evaluate(
        [
            _frame(frame_index=10, timestamp_ms=1000),
            _frame(frame_index=11, timestamp_ms=1100),
        ],
        rules=[_rule(cooldown_seconds=0)],
    )

    assert [event["evidence"]["seen_count"] for event in result["events"]] == [1, 2]


def test_event_engine_reset_clears_callback_state() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _stateful_matching_callback},
    )
    engine.update(_frame(), rules=[_rule()])

    engine.reset()
    result = engine.update(_frame(frame_index=11), rules=[_rule()])

    assert result["events"][0]["evidence"]["seen_count"] == 1


def test_event_engine_summary() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )

    result = engine.evaluate(
        [
            _frame(track_id=7, frame_index=10, timestamp_ms=1000),
            _frame(track_id=8, frame_index=11, timestamp_ms=1100),
        ],
        rules=[_rule(cooldown_seconds=0)],
    )

    assert len(result["events"]) == 2
    assert result["summary"] == {
        "total_events": 2,
        "total_event_evidence": 2,
        "total_rule_executions": 2,
        "per_event_type_counts": {"danger_zone_intrusion": 2},
        "per_rule_status_counts": {"matched": 2},
        "unique_track_ids": 2,
    }


def test_event_engine_record_not_matched_debug() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
        rule_callbacks={"danger_zone_intrusion": _not_matching_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    assert result["events"] == []
    assert result["event_evidence"] == []
    assert result["rule_executions"][0]["status"] == "not_matched"
    assert result["rule_executions"][0]["output_result"]["reason"] == "no_match"


def test_event_rule_from_dict_validates_contract() -> None:
    rule = EventRule.from_dict(
        {
            "rule_id": "rule_001",
            "name": "Mock rule",
            "event_type": "danger_zone_intrusion",
            "enabled": 1,
            "severity": "low",
            "target_classes": ["car", "person"],
            "zone_id": "zone_001",
            "parameters": {"threshold": 1},
            "cooldown_seconds": 2,
            "min_track_length": 3,
        }
    )

    assert rule.enabled is True
    assert rule.target_classes == ("car", "person")
    assert rule.cooldown_seconds == 2.0
    assert rule.min_track_length == 3


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"event_type": "unsupported_event"}, "unsupported event type"),
        ({"severity": "critical"}, "unsupported event severity"),
        ({"parameters": []}, "parameters must be a dict"),
        ({"cooldown_seconds": -1}, "cooldown_seconds must be non-negative"),
        ({"min_track_length": 0}, "min_track_length must be at least 1"),
    ],
)
def test_event_rule_validation_errors(values: dict, message: str) -> None:
    payload = {
        "rule_id": "rule_001",
        "name": "Mock rule",
        "event_type": "danger_zone_intrusion",
    }
    payload.update(values)

    with pytest.raises(ValueError, match=message):
        EventRule.from_dict(payload)


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_001",
        "name": "Mock danger zone rule",
        "event_type": "danger_zone_intrusion",
        "severity": "high",
        "target_classes": (),
        "zone_id": "zone_001",
        "cooldown_seconds": 0,
        "min_track_length": 1,
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
) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "trajectory_points": [
            {
                "track_id": track_id,
                "class_name": class_name,
                "track_length": track_length,
                "speed_px_per_second": 4.2,
            }
        ],
    }


def _matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    return {
        "matched": True,
        "evidence": [
            {
                "evidence_type": "rule",
                "evidence_json": {
                    "reason": "matched by mock rule",
                    "zones_seen": len(zones or []),
                    "engine_run_id": engine_state["run_id"],
                },
            }
        ],
        "reason": "matched by mock rule",
        "input_features": {"track_id": trajectory_point["track_id"]},
        "output_result": {"matched": True},
    }


def _not_matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    return {
        "matched": False,
        "reason": "no_match",
        "input_features": {"track_id": trajectory_point["track_id"]},
        "output_result": {"matched": False},
    }


def _error_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    raise RuntimeError("boom")


def _stateful_matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    state = engine_state["state"].setdefault("test_callback", {"seen_count": 0})
    state["seen_count"] += 1
    return {
        "matched": True,
        "event": {
            "event_type": rule.event_type,
            "evidence": {"seen_count": state["seen_count"]},
        },
        "evidence": [
            {
                "evidence_type": "rule",
                "evidence_json": {"seen_count": state["seen_count"]},
            }
        ],
        "reason": "matched by stateful callback",
        "input_features": {"track_id": trajectory_point["track_id"]},
        "output_result": {"matched": True, "seen_count": state["seen_count"]},
    }


def _execution_reasons(result: dict) -> list[str]:
    return [
        execution["output_result"]["reason"]
        for execution in result["rule_executions"]
    ]
