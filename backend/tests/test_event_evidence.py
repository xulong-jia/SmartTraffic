import pytest

from app.events.evidence import (
    build_event_evidence,
    generate_evidence_id,
    validate_evidence_type,
)
from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_build_event_evidence_defaults() -> None:
    evidence = build_event_evidence(
        event_id="event_001",
        run_id="run_001",
        video_id="video_001",
        evidence_type="trajectory",
        frame_index=10,
        timestamp_ms=1000,
    )

    assert evidence["evidence_id"].startswith("evidence_")
    assert evidence["track_id"] is None
    assert evidence["evidence_json"] == {}
    assert evidence["snapshot_path"] is None
    assert evidence["created_at"]


def test_generate_evidence_id_is_stable() -> None:
    first = generate_evidence_id(
        event_id="event_001",
        evidence_type="zone",
        frame_index=12,
        track_id=7,
    )
    second = generate_evidence_id(
        event_id="event_001",
        evidence_type="zone",
        frame_index=12,
        track_id=7,
    )

    assert first == second
    assert first.startswith("evidence_")


def test_evidence_type_validation() -> None:
    for evidence_type in [
        "trajectory",
        "zone",
        "speed",
        "direction",
        "dwell",
        "rule",
        "line_crossing",
        "zone_statistics",
    ]:
        assert validate_evidence_type(evidence_type) == evidence_type

    with pytest.raises(ValueError):
        validate_evidence_type("snapshot")


def test_build_event_evidence_accepts_empty_payload_and_no_snapshot() -> None:
    evidence = build_event_evidence(
        event_id="event_001",
        run_id="run_001",
        video_id="video_001",
        evidence_type="rule",
    )

    assert evidence["evidence_json"] == {}
    assert evidence["snapshot_path"] is None


def test_build_event_evidence_rejects_absolute_snapshot_path() -> None:
    with pytest.raises(ValueError):
        build_event_evidence(
            event_id="event_001",
            run_id="run_001",
            video_id="video_001",
            evidence_type="trajectory",
            snapshot_path="/tmp/private/snapshot.jpg",
        )


def test_event_engine_enriches_matched_evidence_with_rule_context() -> None:
    engine = EventEngine(
        run_id="run_001",
        video_id="video_001",
        rule_callbacks={"wrong_way_driving": _matching_callback},
    )

    result = engine.update(
        _frame(),
        rules=[
            EventRule(
                rule_id="rule_wrong_way",
                name="Wrong Way",
                event_type="wrong_way_driving",
                zone_id="lane_1",
                parameters={"allowed_angle": 0, "angle_tolerance": 30},
            )
        ],
    )

    event = result["events"][0]
    evidence = result["event_evidence"][0]
    evidence_json = evidence["evidence_json"]
    assert evidence["event_id"] == event["event_id"]
    assert evidence["event_type"] == "wrong_way_driving"
    assert evidence["zone_id"] == "lane_1"
    assert evidence["rule_id"] == "rule_wrong_way"
    assert evidence_json["bbox"] == [10, 20, 30, 40]
    assert evidence_json["center"] == [20, 30]
    assert evidence_json["speed"] == 3.5
    assert evidence_json["moving_angle"] == 180
    assert evidence_json["allowed_angle"] == 0
    assert evidence_json["angle_diff"] == 180
    assert evidence_json["rule_parameters"] == {
        "allowed_angle": 0,
        "angle_tolerance": 30,
    }
    assert evidence_json["trigger_reason"] == "wrong_way_direction_detected"
    assert evidence_json["snapshot_available"] is False
    assert evidence_json["snapshot_reason"] == (
        "frame image not available in current artifact pipeline"
    )


def _frame() -> dict:
    return {
        "frame_index": 12,
        "timestamp_ms": 1200,
        "trajectory_points": [
            {
                "track_id": 7,
                "class_name": "car",
                "bbox": [10, 20, 30, 40],
                "center": [20, 30],
                "bottom_center": [20, 40],
                "speed_px_per_frame": 3.5,
                "moving_angle": 180,
                "dwell_time_ms": 0,
                "track_length": 4,
            }
        ],
    }


def _matching_callback(rule, trajectory_point, frame_result, zones, engine_state) -> dict:
    return {
        "matched": True,
        "reason": "wrong_way_direction_detected",
        "evidence": [
            {
                "evidence_type": "direction",
                "evidence_json": {
                    "direction_angle": 180,
                    "allowed_angle": 0,
                    "angle_diff": 180,
                },
            }
        ],
        "input_features": {
            "track_id": trajectory_point["track_id"],
            "moving_angle": trajectory_point["moving_angle"],
        },
        "output_result": {
            "matched": True,
            "reason": "wrong_way_direction_detected",
        },
    }
