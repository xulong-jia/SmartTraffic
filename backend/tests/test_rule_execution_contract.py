import pytest

from app.events.rule_execution import (
    build_rule_execution,
    generate_rule_execution_id,
    validate_rule_execution_status,
)


def test_build_rule_execution_defaults() -> None:
    execution = build_rule_execution(
        run_id="run_001",
        rule_id="rule_001",
        frame_index=10,
        status="skipped",
    )

    assert execution["execution_id"].startswith("execution_")
    assert execution["event_id"] is None
    assert execution["track_id"] is None
    assert execution["input_features"] == {}
    assert execution["output_result"] == {}
    assert execution["created_at"]


def test_generate_rule_execution_id_is_stable() -> None:
    first = generate_rule_execution_id(
        run_id="run_001",
        rule_id="rule_001",
        track_id=7,
        frame_index=10,
        status="matched",
    )
    second = generate_rule_execution_id(
        run_id="run_001",
        rule_id="rule_001",
        track_id=7,
        frame_index=10,
        status="matched",
    )

    assert first == second
    assert first.startswith("execution_")


def test_rule_execution_status_validation() -> None:
    for status in ["matched", "not_matched", "skipped", "error"]:
        assert validate_rule_execution_status(status) == status

    with pytest.raises(ValueError):
        validate_rule_execution_status("pending")


def test_build_rule_execution_accepts_event_id_none_for_skipped_or_error() -> None:
    skipped = build_rule_execution(
        run_id="run_001",
        rule_id="rule_001",
        event_id=None,
        status="skipped",
    )
    error = build_rule_execution(
        run_id="run_001",
        rule_id="rule_001",
        event_id=None,
        status="error",
    )

    assert skipped["event_id"] is None
    assert error["event_id"] is None


def test_build_rule_execution_accepts_empty_input_and_output() -> None:
    execution = build_rule_execution(
        run_id="run_001",
        rule_id="rule_001",
        status="not_matched",
    )

    assert execution["input_features"] == {}
    assert execution["output_result"] == {}
