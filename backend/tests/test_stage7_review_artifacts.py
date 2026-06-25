import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.review_artifacts import (
    REVIEW_ARTIFACTS,
    ReviewStateTransitionError,
    append_false_negative,
    append_review_comment,
    apply_review_action,
    current_event_review_status,
    load_event_review_state,
    load_false_negatives,
    load_review_comments,
)


def test_missing_review_files_load_as_empty_artifacts(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)

    assert load_review_comments(run_dir) == []
    assert load_false_negatives(run_dir) == []
    assert load_event_review_state(run_dir, run_id="run_stage7b") == {
        "schema_version": "stage7b.v1",
        "run_id": "run_stage7b",
        "updated_at": None,
        "events": {},
    }
    assert current_event_review_status(run_dir, "event_missing") == "pending"


def test_append_review_comment_is_append_only_and_updates_metadata(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)

    first = append_review_comment(
        run_dir,
        {
            "run_id": "run_stage7b",
            "event_id": "event_1",
            "action": "comment",
            "before_status": "pending",
            "after_status": "pending",
            "comment": "first note",
        },
    )
    second = append_review_comment(
        run_dir,
        {
            "run_id": "run_stage7b",
            "event_id": "event_1",
            "action": "comment",
            "before_status": "pending",
            "after_status": "pending",
            "comment": "second note",
        },
    )

    rows = _read_jsonl(run_dir / "review_comments.jsonl")
    assert [row["comment"] for row in rows] == ["first note", "second note"]
    assert [row["review_id"] for row in rows] == [
        first["review_id"],
        second["review_id"],
    ]
    assert first["review_id"] != second["review_id"]
    assert first["review_id"].startswith("review_")
    assert first["reviewer"] == "local_reviewer"
    assert first["source"] == "review_center"
    assert _metadata_artifacts(run_dir)["review_comments"] == "review_comments.jsonl"


def test_apply_confirm_writes_audit_record_and_state_without_touching_events(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)
    original_events = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    result = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="confirm",
        comment="confirmed by reviewer",
        reviewer="reviewer_1",
        alert_id="alert_1",
    )

    comments = load_review_comments(run_dir)
    state = load_event_review_state(run_dir, run_id="run_stage7b")
    event_state = state["events"]["event_1"]
    assert result["status"] == "confirmed"
    assert comments[-1]["action"] == "confirm"
    assert comments[-1]["before_status"] == "pending"
    assert comments[-1]["after_status"] == "confirmed"
    assert comments[-1]["alert_id"] == "alert_1"
    assert event_state["status"] == "confirmed"
    assert event_state["last_action"] == "confirm"
    assert event_state["last_review_id"] == comments[-1]["review_id"]
    assert event_state["reviewer"] == "reviewer_1"
    assert event_state["comment_count"] == 1
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == original_events


def test_apply_false_positive_ignore_and_resolve_transitions(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)

    false_positive = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="mark_false_positive",
    )
    resolved_false_positive = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="resolve",
    )
    ignored = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_2",
        action="ignore",
    )
    resolved_ignored = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_2",
        action="resolve",
    )

    assert false_positive["status"] == "false_positive"
    assert resolved_false_positive["status"] == "resolved"
    assert ignored["status"] == "ignored"
    assert resolved_ignored["status"] == "resolved"
    assert current_event_review_status(run_dir, "event_1") == "resolved"
    assert current_event_review_status(run_dir, "event_2") == "resolved"


def test_comment_action_preserves_status_and_increments_comment_count(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)
    apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="confirm",
    )

    result = apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="comment",
        comment="follow-up note",
    )

    event_state = load_event_review_state(run_dir, run_id="run_stage7b")["events"][
        "event_1"
    ]
    assert result["status"] == "confirmed"
    assert event_state["status"] == "confirmed"
    assert event_state["last_action"] == "comment"
    assert event_state["comment_count"] == 2
    assert load_review_comments(run_dir)[-1]["before_status"] == "confirmed"
    assert load_review_comments(run_dir)[-1]["after_status"] == "confirmed"


def test_invalid_transition_raises_clear_error_and_does_not_write(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)
    apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="confirm",
    )

    with pytest.raises(
        ReviewStateTransitionError,
        match="cannot apply mark_false_positive from confirmed",
    ):
        apply_review_action(
            run_dir,
            run_id="run_stage7b",
            event_id="event_1",
            action="mark_false_positive",
        )

    comments = load_review_comments(run_dir)
    assert [comment["action"] for comment in comments] == ["confirm"]
    assert current_event_review_status(run_dir, "event_1") == "confirmed"


def test_append_false_negative_writes_record_and_audit_artifacts(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)

    first = append_false_negative(
        run_dir,
        {
            "run_id": "run_stage7b",
            "expected_event_type": "wrong_way_driving",
            "description": "Reviewer found a missed wrong-way event.",
            "start_frame": 100,
            "end_frame": 150,
        },
    )
    second = append_false_negative(
        run_dir,
        {
            "run_id": "run_stage7b",
            "expected_event_type": "illegal_parking",
            "track_id": None,
            "zone_id": None,
            "description": "Optional track and zone are allowed.",
        },
    )

    records = load_false_negatives(run_dir)
    comments = load_review_comments(run_dir)
    state = load_event_review_state(run_dir, run_id="run_stage7b")
    assert [record["false_negative_id"] for record in records] == [
        first["false_negative_id"],
        second["false_negative_id"],
    ]
    assert first["false_negative_id"] != second["false_negative_id"]
    assert first["false_negative_id"].startswith("fn_")
    assert second["track_id"] is None
    assert second["zone_id"] is None
    assert records[0]["status"] == "false_negative"
    assert comments[-2]["action"] == "add_false_negative"
    assert comments[-1]["action"] == "add_false_negative"
    assert state["events"][first["false_negative_id"]]["status"] == "false_negative"
    assert state["events"][second["false_negative_id"]]["status"] == "false_negative"


def test_review_artifacts_are_added_to_manifest_and_artifact_index(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path, write_manifest=True)

    apply_review_action(
        run_dir,
        run_id="run_stage7b",
        event_id="event_1",
        action="confirm",
    )
    append_false_negative(
        run_dir,
        {
            "run_id": "run_stage7b",
            "expected_event_type": "wrong_way_driving",
            "description": "missed event",
        },
    )

    manifest = _read_json(run_dir / "manifest.json")
    artifact_index = _read_json(run_dir / "artifact_index.json")
    metadata = _read_json(run_dir / "metadata.json")
    for key, path in REVIEW_ARTIFACTS.items():
        assert manifest["artifacts"][key]["status"] == "available"
        assert manifest["artifacts"][key]["path"] == path
        assert artifact_index["artifacts"][key] == path
        assert metadata["artifacts"][key] == path
        assert metadata["artifact_summary"][key]["status"] == "available"


def _create_run(tmp_path: Path, *, write_manifest: bool = False) -> Path:
    run_id = "run_stage7b"
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "status": "completed",
            "mode": "offline",
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            {
                "event_id": "event_1",
                "run_id": run_id,
                "video_id": "video_001",
                "event_type": "wrong_way_driving",
                "status": "pending",
            },
            {
                "event_id": "event_2",
                "run_id": run_id,
                "video_id": "video_001",
                "event_type": "illegal_parking",
                "status": "pending",
            },
        ],
        event_evidence=[],
        rule_executions=[],
    )
    if write_manifest:
        writer.write_run_manifest(run_id, status="completed")
    return tmp_path / run_id


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _metadata_artifacts(run_dir: Path) -> dict:
    return _read_json(run_dir / "metadata.json")["artifacts"]
