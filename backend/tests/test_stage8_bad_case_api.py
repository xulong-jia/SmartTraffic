import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.evaluation_artifacts import append_failed_case
from app.analysis.review_artifacts import append_review_comment
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_bad_case_list_missing_artifact_returns_empty_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)

    response = client.get(f"/api/bad-cases?run_id={run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert payload["summary"]["total"] == 0
    assert payload["summary"]["by_type"] == {}
    assert payload["summary"]["by_tag"] == {}


def test_bad_case_create_list_detail_update_and_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)

    created = client.post(
        "/api/bad-cases",
        json={
            "run_id": run_id,
            "event_id": "event_danger",
            "track_id": 17,
            "frame_index": 10,
            "case_type": "false_positive",
            "module": "event_engine",
            "description": "Wrong-way event was not valid.",
            "expected_result": "no event",
            "actual_result": "wrong_way_driving",
            "root_cause": "direction threshold too sensitive",
            "snapshot_path": "keyframes/event_danger.jpg",
            "tags": ["wrong_way", "rule_threshold"],
        },
    )

    assert created.status_code == 200
    case = created.json()
    assert case["case_id"].startswith("badcase_")
    assert case["run_id"] == run_id
    assert case["video_id"] == "video_001"
    assert case["status"] == "open"

    listed = client.get(f"/api/bad-cases?run_id={run_id}")
    detail = client.get(f"/api/bad-cases/{case['case_id']}?run_id={run_id}")
    patched = client.patch(
        f"/api/bad-cases/{case['case_id']}",
        json={
            "run_id": run_id,
            "status": "fixed",
            "root_cause": "rule threshold fixed",
            "tags": ["wrong_way", "fixed"],
            "description": "Updated after rule config change.",
        },
    )
    summary = client.get(f"/api/bad-cases/summary?run_id={run_id}")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["case_id"] == case["case_id"]
    assert listed.json()["summary"]["by_type"] == {"false_positive": 1}
    assert listed.json()["summary"]["by_tag"]["wrong_way"] == 1
    assert detail.status_code == 200
    assert detail.json()["case_id"] == case["case_id"]
    assert patched.status_code == 200
    assert patched.json()["status"] == "fixed"
    assert patched.json()["root_cause"] == "rule threshold fixed"
    assert patched.json()["tags"] == ["wrong_way", "fixed"]
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["by_status"] == {"fixed": 1}
    assert summary.json()["by_tag"] == {"wrong_way": 1, "fixed": 1}


def test_bad_case_filters_by_case_type_module_status_tag_and_run_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_a = _create_bad_case_run(tmp_path, run_id="run_bad_case_a")
    run_b = _create_bad_case_run(tmp_path, run_id="run_bad_case_b")
    case_a = _create_case(
        client,
        run_id=run_a,
        case_type="false_positive",
        module="event_engine",
        tags=["wrong_way"],
    )
    _create_case(
        client,
        run_id=run_a,
        case_type="tracking_fragmentation",
        module="tracker",
        tags=["identity"],
    )
    _create_case(
        client,
        run_id=run_b,
        case_type="false_negative",
        module="detector",
        tags=["missed"],
    )
    client.patch(
        f"/api/bad-cases/{case_a['case_id']}",
        json={"run_id": run_a, "status": "fixed"},
    )

    response = client.get(
        "/api/bad-cases"
        f"?run_id={run_a}&case_type=false_positive&module=event_engine&status=fixed&tag=wrong_way"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["case_id"] == case_a["case_id"]
    assert payload["summary"]["total"] == 1


def test_bad_case_from_review_creates_reference_without_mutating_review_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)
    run_dir = tmp_path / "results" / run_id
    review = append_review_comment(
        run_dir,
        {
            "run_id": run_id,
            "event_id": "event_danger",
            "action": "mark_false_positive",
            "before_status": "pending",
            "after_status": "false_positive",
            "comment": "Reviewer marked as false positive.",
        },
    )
    original_review_comments = (run_dir / "review_comments.jsonl").read_text(
        encoding="utf-8"
    )

    response = client.post(
        "/api/bad-cases/from-review",
        json={
            "run_id": run_id,
            "review_id": review["review_id"],
            "case_type": "false_positive",
            "module": "review_center",
            "description": "Promoted from review.",
            "tags": ["reviewed"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "review_center"
    assert payload["linked_review_id"] == review["review_id"]
    assert payload["event_id"] == "event_danger"
    assert (run_dir / "review_comments.jsonl").read_text(
        encoding="utf-8"
    ) == original_review_comments


def test_bad_case_from_failed_case_creates_evaluation_reference_and_deduplicates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)
    failed_case = append_failed_case(
        tmp_path / "evals",
        {
            "failed_case_id": "failed_eval_1",
            "evaluation_run_id": "eval_run_1",
            "run_id": run_id,
            "failure_type": "false_negative",
            "module": "event_engine",
            "expected": {"event_type": "illegal_parking"},
            "actual": {},
            "frame_range": {"start_frame": 40, "end_frame": 50},
            "suggested_bad_case_type": "false_negative",
            "created_at": "2026-01-01T00:00:01+00:00",
        },
    )

    first = client.post(
        "/api/bad-cases/from-failed-case",
        json={
            "run_id": run_id,
            "failed_case_id": failed_case["failed_case_id"],
            "description": "Converted from evaluation failed case.",
            "root_cause": "to be analyzed",
            "tags": ["evaluation"],
        },
    )
    second = client.post(
        "/api/bad-cases/from-failed-case",
        json={"run_id": run_id, "failed_case_id": failed_case["failed_case_id"]},
    )
    missing = client.post(
        "/api/bad-cases/from-failed-case",
        json={"run_id": run_id, "failed_case_id": "missing_failed_case"},
    )

    assert first.status_code == 200
    payload = first.json()
    assert payload["source"] == "evaluation_center"
    assert payload["case_type"] == "false_negative"
    assert payload["module"] == "event_engine"
    assert payload["linked_failed_case_id"] == failed_case["failed_case_id"]
    assert payload["root_cause"] == "to be analyzed"
    assert second.status_code == 200
    assert second.json()["case_id"] == payload["case_id"]
    assert missing.status_code == 404
    assert missing.json()["detail"] == "failed case not found"


def test_bad_case_api_missing_resources_and_invalid_artifact_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)

    missing_run = client.get("/api/bad-cases?run_id=missing_run")
    missing_case = client.get(f"/api/bad-cases/missing_case?run_id={run_id}")
    missing_review = client.post(
        "/api/bad-cases/from-review",
        json={"run_id": run_id, "review_id": "missing_review"},
    )
    (tmp_path / "results" / run_id / "bad_cases.jsonl").write_text(
        "{bad json\n",
        encoding="utf-8",
    )
    malformed = client.get(f"/api/bad-cases?run_id={run_id}")

    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "analysis run not found"
    assert missing_case.status_code == 404
    assert missing_case.json()["detail"] == "bad case not found"
    assert missing_review.status_code == 404
    assert missing_review.json()["detail"] == "review not found"
    assert malformed.status_code == 400
    assert malformed.json()["detail"] == "invalid bad case artifact"


def test_bad_case_api_invalid_enum_returns_validation_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_bad_case_run(tmp_path)

    response = client.post(
        "/api/bad-cases",
        json={
            "run_id": run_id,
            "case_type": "not_supported",
            "module": "event_engine",
        },
    )

    assert response.status_code == 422


def _client_for_tmp_results(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("SMARTTRAFFIC_EVALS_DIR", str(tmp_path / "evals"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_bad_case_run(tmp_path: Path, *, run_id: str = "run_stage8cd") -> str:
    writer = TrafficArtifactWriter(tmp_path / "results")
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
                "event_id": "event_danger",
                "run_id": run_id,
                "video_id": "video_001",
                "event_type": "wrong_way_driving",
                "severity": "high",
                "track_id": 17,
                "frame_index": 10,
                "status": "pending",
            }
        ],
        event_evidence=[],
        rule_executions=[],
    )
    writer.write_run_manifest(run_id, status="completed")
    return run_id


def _create_case(
    client: TestClient,
    *,
    run_id: str,
    case_type: str,
    module: str,
    tags: list[str],
) -> dict:
    response = client.post(
        "/api/bad-cases",
        json={
            "run_id": run_id,
            "case_type": case_type,
            "module": module,
            "description": f"{case_type} case",
            "tags": tags,
        },
    )
    assert response.status_code == 200
    return response.json()
