from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_matched_rule_execution_links_event_id_and_stable_fields() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"danger_zone_intrusion": _matching_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    event = result["events"][0]
    execution = result["rule_executions"][0]
    assert execution["run_id"] == "run_001"
    assert execution["rule_id"] == "rule_001"
    assert execution["event_id"] == event["event_id"]
    assert execution["track_id"] == 7
    assert execution["frame_index"] == 10
    assert execution["status"] == "matched"
    assert execution["input_features"]["bbox"] == [40, 20, 60, 50]
    assert execution["output_result"]["matched"] is True
    assert execution["output_result"]["reason"] == "inside_danger_zone"
    assert execution["created_at"]


def test_not_matched_rule_execution_records_reason_when_debug_enabled() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        record_not_matched=True,
        rule_callbacks={"danger_zone_intrusion": _not_matching_callback},
    )

    result = engine.update(_frame(), rules=[_rule()])

    assert result["events"] == []
    execution = result["rule_executions"][0]
    assert execution["status"] == "not_matched"
    assert execution["event_id"] is None
    assert execution["input_features"]["track_id"] == 7
    assert execution["output_result"]["matched"] is False
    assert execution["output_result"]["reason"] == "outside_danger_zone"


def test_rule_callback_error_records_execution_without_interrupting_run() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={
            "rule_error": _error_callback,
            "rule_match": _matching_callback,
        },
    )

    result = engine.update(
        _frame(),
        rules=[
            _rule(rule_id="rule_error"),
            _rule(rule_id="rule_match"),
        ],
    )

    assert len(result["events"]) == 1
    statuses = [execution["status"] for execution in result["rule_executions"]]
    assert statuses == ["error", "matched"]
    error_execution = result["rule_executions"][0]
    assert error_execution["event_id"] is None
    assert error_execution["output_result"]["reason"] == "rule_error"
    assert error_execution["output_result"]["error_type"] == "RuntimeError"
    assert error_execution["output_result"]["error"] == "boom"
    assert "Traceback" not in error_execution["output_result"]["error"]


def _rule(**overrides) -> EventRule:
    values = {
        "rule_id": "rule_001",
        "name": "Danger Zone Rule",
        "event_type": "danger_zone_intrusion",
        "zone_id": "danger_zone_1",
        "parameters": {"min_inside_frames": 1},
    }
    values.update(overrides)
    return EventRule(**values)


def _frame() -> dict:
    return {
        "frame_index": 10,
        "timestamp_ms": 1000,
        "trajectory_points": [
            {
                "track_id": 7,
                "class_name": "car",
                "track_length": 3,
                "bbox": [40, 20, 60, 50],
                "center": [50, 35],
                "bottom_center": [50, 50],
                "speed_px_per_frame": 1.2,
            }
        ],
    }


def _matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    return {
        "matched": True,
        "reason": "inside_danger_zone",
        "input_features": {
            "track_id": trajectory_point["track_id"],
            "bbox": trajectory_point["bbox"],
        },
        "output_result": {
            "matched": True,
            "reason": "inside_danger_zone",
        },
        "evidence": [
            {
                "evidence_type": "zone",
                "evidence_json": {"trigger_reason": "inside_danger_zone"},
            }
        ],
    }


def _not_matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    return {
        "matched": False,
        "reason": "outside_danger_zone",
        "input_features": {
            "track_id": trajectory_point["track_id"],
            "bbox": trajectory_point["bbox"],
        },
        "output_result": {
            "matched": False,
            "reason": "outside_danger_zone",
        },
    }


def _error_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    raise RuntimeError("boom")
