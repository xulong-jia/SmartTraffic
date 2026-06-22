import pytest

from app.events.contracts import (
    build_event,
    generate_event_id,
    validate_event_severity,
    validate_event_status,
)


def test_build_event_defaults() -> None:
    event = build_event(
        run_id="run_001",
        video_id="video_001",
        event_type="danger_zone_intrusion",
        start_frame=10,
        end_frame=12,
        start_time_ms=1000,
        end_time_ms=1200,
    )

    assert event["event_id"].startswith("event_")
    assert event["severity"] == "medium"
    assert event["status"] == "pending"
    assert event["confidence"] == 1.0
    assert event["evidence"] == {}
    assert event["track_id"] is None
    assert event["zone_id"] is None
    assert event["created_at"]


def test_generate_event_id_is_stable() -> None:
    first = generate_event_id(
        run_id="run_001",
        event_type="danger_zone_intrusion",
        track_id=7,
        zone_id="zone_a",
        rule_id="rule_a",
        start_frame=10,
        end_frame=12,
    )
    second = generate_event_id(
        run_id="run_001",
        event_type="danger_zone_intrusion",
        track_id=7,
        zone_id="zone_a",
        rule_id="rule_a",
        start_frame=10,
        end_frame=12,
    )

    assert first == second
    assert first.startswith("event_")


def test_event_severity_validation() -> None:
    assert validate_event_severity("low") == "low"
    assert validate_event_severity("medium") == "medium"
    assert validate_event_severity("high") == "high"
    with pytest.raises(ValueError):
        validate_event_severity("critical")


def test_event_status_validation() -> None:
    assert validate_event_status("pending") == "pending"
    assert validate_event_status("confirmed") == "confirmed"
    assert validate_event_status("false_positive") == "false_positive"
    assert validate_event_status("false_negative") == "false_negative"
    assert validate_event_status("ignored") == "ignored"
    assert validate_event_status("resolved") == "resolved"
    with pytest.raises(ValueError):
        validate_event_status("new")


def test_build_event_accepts_optional_track_and_zone() -> None:
    event = build_event(
        run_id="run_001",
        video_id="video_001",
        event_type="illegal_parking",
        track_id=None,
        zone_id=None,
    )

    assert event["track_id"] is None
    assert event["zone_id"] is None


def test_build_event_does_not_include_review_bad_case_or_evaluation_fields() -> None:
    event = build_event(
        run_id="run_001",
        video_id="video_001",
        event_type="danger_zone_intrusion",
    )

    forbidden_fields = {
        "review_status",
        "review_comments",
        "bad_case_id",
        "evaluation_result_id",
    }
    assert forbidden_fields.isdisjoint(event)
