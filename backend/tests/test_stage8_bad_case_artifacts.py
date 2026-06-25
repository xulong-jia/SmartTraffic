import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.bad_case_artifacts import (
    BAD_CASE_ARTIFACTS,
    BadCaseArtifactError,
    load_bad_cases,
)
from app.analysis.review_artifacts import append_review_comment
from app.services.bad_case_service import BadCaseService


def test_missing_bad_case_file_loads_as_empty_artifact(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)

    assert load_bad_cases(run_dir) == []


def test_create_bad_case_writes_jsonl_and_updates_manifest_metadata(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path, write_manifest=True)
    service = BadCaseService(artifact_writer=TrafficArtifactWriter(tmp_path))

    case = service.create_bad_case(
        run_id="run_stage8b",
        record={
            "event_id": "event_1",
            "track_id": 7,
            "frame_index": 42,
            "case_type": "false_positive",
            "module": "event_engine",
            "description": "wrong-way event was triggered on a normal track",
            "expected_result": "no event should be generated",
            "actual_result": "wrong_way_driving event was generated",
            "snapshot_path": "keyframes/event_1.jpg",
            "tags": ["wrong_way", "reviewed"],
        },
    )

    rows = _read_jsonl(run_dir / "bad_cases.jsonl")
    assert [row["case_id"] for row in rows] == [case["case_id"]]
    assert case["case_id"].startswith("badcase_")
    assert case["run_id"] == "run_stage8b"
    assert case["video_id"] == "video_001"
    assert case["status"] == "open"
    assert case["source"] == "manual"
    assert case["root_cause"] == ""
    assert case["snapshot_path"] == "keyframes/event_1.jpg"
    assert case["tags"] == ["wrong_way", "reviewed"]

    manifest = _read_json(run_dir / "manifest.json")
    artifact_index = _read_json(run_dir / "artifact_index.json")
    metadata = _read_json(run_dir / "metadata.json")
    assert manifest["artifacts"]["bad_cases"]["status"] == "available"
    assert manifest["artifacts"]["bad_cases"]["path"] == "bad_cases.jsonl"
    assert artifact_index["artifacts"]["bad_cases"] == "bad_cases.jsonl"
    assert metadata["artifacts"]["bad_cases"] == "bad_cases.jsonl"
    assert metadata["artifact_summary"]["bad_cases"]["record_count"] == 1


def test_bad_case_ids_are_unique_and_optional_fields_may_be_none(
    tmp_path: Path,
) -> None:
    service = BadCaseService(artifact_writer=TrafficArtifactWriter(tmp_path))
    _create_run(tmp_path)

    first = service.create_bad_case(
        run_id="run_stage8b",
        record={
            "case_type": "false_negative",
            "module": "detector",
            "description": "missed vehicle",
        },
    )
    second = service.create_bad_case(
        run_id="run_stage8b",
        record={
            "case_type": "false_negative",
            "module": "detector",
            "description": "missed vehicle",
        },
    )

    assert first["case_id"] != second["case_id"]
    assert first["event_id"] is None
    assert first["track_id"] is None
    assert first["snapshot_path"] is None


def test_list_detail_update_and_summary_are_service_level_artifact_backed(
    tmp_path: Path,
) -> None:
    service = BadCaseService(artifact_writer=TrafficArtifactWriter(tmp_path))
    _create_run(tmp_path, write_manifest=True)

    first = service.create_bad_case(
        run_id="run_stage8b",
        record={
            "event_id": "event_1",
            "case_type": "false_positive",
            "module": "event_engine",
            "description": "normal track flagged as wrong way",
            "tags": ["wrong_way"],
        },
    )
    service.create_bad_case(
        run_id="run_stage8b",
        record={
            "event_id": "event_2",
            "case_type": "tracking_fragmentation",
            "module": "tracker",
            "description": "track id switched",
            "tags": ["identity"],
        },
    )

    updated = service.update_bad_case(
        run_id="run_stage8b",
        case_id=first["case_id"],
        updates={
            "status": "fixed",
            "root_cause": "event rule threshold was too permissive",
            "tags": ["wrong_way", "rule_threshold"],
        },
    )

    assert updated["status"] == "fixed"
    assert updated["root_cause"] == "event rule threshold was too permissive"
    assert service.get_bad_case(
        run_id="run_stage8b",
        case_id=first["case_id"],
    )["tags"] == ["wrong_way", "rule_threshold"]
    assert [
        item["case_id"]
        for item in service.list_bad_cases(run_id="run_stage8b", status="fixed")
    ] == [first["case_id"]]
    assert [
        item["case_id"]
        for item in service.list_bad_cases(run_id="run_stage8b", tag="identity")
    ] == [service.list_bad_cases(run_id="run_stage8b", module="tracker")[0]["case_id"]]

    summary = service.summarize_bad_cases(run_id="run_stage8b")
    assert summary["total"] == 2
    assert summary["by_type"] == {
        "false_positive": 1,
        "tracking_fragmentation": 1,
    }
    assert summary["by_status"] == {"fixed": 1, "open": 1}
    assert summary["by_module"] == {"event_engine": 1, "tracker": 1}
    assert summary["top_tags"]["wrong_way"] == 1

    audit_rows = _read_jsonl(tmp_path / "run_stage8b" / "bad_case_updates.jsonl")
    assert audit_rows == [
        {
            "case_id": first["case_id"],
            "run_id": "run_stage8b",
            "updated_fields": ["root_cause", "status", "tags"],
            "updated_at": updated["updated_at"],
            "source": "bad_case_service",
        }
    ]


def test_create_from_review_links_review_without_mutating_review_artifacts(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path, write_manifest=True)
    review = append_review_comment(
        run_dir,
        {
            "run_id": "run_stage8b",
            "event_id": "event_1",
            "action": "mark_false_positive",
            "before_status": "pending",
            "after_status": "false_positive",
            "comment": "Reviewer marked this event as false positive.",
            "reviewer": "reviewer_1",
        },
    )
    original_review_comments = (run_dir / "review_comments.jsonl").read_text(
        encoding="utf-8"
    )
    service = BadCaseService(artifact_writer=TrafficArtifactWriter(tmp_path))

    case = service.create_bad_case_from_review(
        run_id="run_stage8b",
        review_id=review["review_id"],
    )

    assert case["event_id"] == "event_1"
    assert case["case_type"] == "false_positive"
    assert case["module"] == "review_center"
    assert case["source"] == "review_center"
    assert case["linked_review_id"] == review["review_id"]
    assert "Reviewer marked this event" in case["description"]
    assert (run_dir / "review_comments.jsonl").read_text(
        encoding="utf-8"
    ) == original_review_comments


def test_malformed_jsonl_raises_clear_bad_case_artifact_error(
    tmp_path: Path,
) -> None:
    run_dir = _create_run(tmp_path)
    (run_dir / "bad_cases.jsonl").write_text("{bad json\n", encoding="utf-8")

    with pytest.raises(BadCaseArtifactError, match="malformed bad case artifact"):
        load_bad_cases(run_dir)


def test_bad_case_artifacts_are_declared_for_stage8b() -> None:
    assert BAD_CASE_ARTIFACTS == {
        "bad_cases": "bad_cases.jsonl",
        "bad_case_updates": "bad_case_updates.jsonl",
    }


def _create_run(tmp_path: Path, *, write_manifest: bool = False) -> Path:
    run_id = "run_stage8b"
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
                "track_id": 7,
                "start_frame": 40,
                "end_frame": 55,
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
