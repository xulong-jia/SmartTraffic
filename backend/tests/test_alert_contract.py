import pytest

from app.alerts.contracts import (
    build_alert,
    generate_alert_id,
    severity_to_alert_level,
    validate_alert_status,
)


def test_generate_alert_id_is_stable() -> None:
    first = generate_alert_id(
        run_id="run_001",
        event_id="event_001",
        alert_type="illegal_parking",
    )
    second = generate_alert_id(
        run_id="run_001",
        event_id="event_001",
        alert_type="illegal_parking",
    )

    assert first == second
    assert first.startswith("alert_")


def test_severity_to_alert_level() -> None:
    assert severity_to_alert_level("low") == "info"
    assert severity_to_alert_level("medium") == "warning"
    assert severity_to_alert_level("high") == "critical"
    assert severity_to_alert_level("unexpected") == "warning"
    assert severity_to_alert_level(None) == "warning"


def test_build_alert_defaults() -> None:
    alert = build_alert(
        event_id="event_001",
        run_id="run_001",
        video_id="video_001",
        event_type="danger_zone_intrusion",
        severity="high",
        track_id=7,
        zone_id="zone_001",
        frame_index=10,
        timestamp_ms=1000,
    )

    assert alert["alert_id"].startswith("alert_")
    assert alert["alert_type"] == "danger_zone_intrusion"
    assert alert["level"] == "critical"
    assert alert["status"] == "new"
    assert alert["title"] == "Danger zone intrusion"
    assert alert["message"]
    assert alert["created_at"]


def test_build_alert_missing_severity_defaults_to_warning() -> None:
    alert = build_alert(
        event_id="event_001",
        run_id="run_001",
        video_id="video_001",
        event_type="illegal_parking",
        severity=None,
    )

    assert alert["level"] == "warning"


def test_validate_alert_status() -> None:
    assert validate_alert_status("new") == "new"
    assert validate_alert_status("acknowledged") == "acknowledged"
    assert validate_alert_status("resolved") == "resolved"
    assert validate_alert_status("ignored") == "ignored"
    with pytest.raises(ValueError):
        validate_alert_status("closed")


def test_build_alert_does_not_include_review_bad_case_or_evaluation_fields() -> None:
    alert = build_alert(
        event_id="event_001",
        run_id="run_001",
        video_id="video_001",
        event_type="illegal_parking",
    )

    forbidden_fields = {
        "review_status",
        "reviewer",
        "bad_case_id",
        "evaluation_result",
        "ground_truth",
    }
    assert forbidden_fields.isdisjoint(alert)
