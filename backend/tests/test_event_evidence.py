import pytest

from app.events.evidence import (
    build_event_evidence,
    generate_evidence_id,
    validate_evidence_type,
)


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
    for evidence_type in ["trajectory", "zone", "speed", "direction", "dwell", "rule"]:
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
