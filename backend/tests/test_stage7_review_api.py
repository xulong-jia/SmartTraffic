import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_review_events_requires_run_id(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)

    response = client.get("/api/review/events")

    assert response.status_code == 400
    assert response.json()["detail"] == "run_id is required"


def test_review_events_lists_events_with_review_state_and_linked_alerts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)
    client.post(
        "/api/review/events/event_danger/confirm",
        json={
            "run_id": run_id,
            "comment": "confirmed",
            "reviewer": "reviewer_1",
            "alert_id": "alert_danger",
        },
    )

    response = client.get(f"/api/review/events?run_id={run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    first = payload["items"][0]
    assert first["run_id"] == run_id
    assert first["event_id"] == "event_danger"
    assert first["event_type"] == "danger_zone_intrusion"
    assert first["original_status"] == "pending"
    assert first["review_status"] == "confirmed"
    assert first["last_action"] == "confirm"
    assert first["comment_count"] == 1
    assert first["linked_alert_ids"] == ["alert_danger"]
    assert first["start_frame"] == 10
    assert first["end_time_ms"] == 1000


def test_review_events_filters_by_status_event_type_and_paginates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)
    client.post(
        "/api/review/events/event_danger/false-positive",
        json={"run_id": run_id},
    )

    response = client.get(
        f"/api/review/events?run_id={run_id}&status=false_positive&event_type=danger_zone_intrusion&limit=1&offset=0"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_id"] == "event_danger"
    assert payload["items"][0]["review_status"] == "false_positive"


def test_review_event_detail_returns_event_comments_alerts_and_visual_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path, with_visual_artifacts=True)
    client.post(
        "/api/review/events/event_danger/confirm",
        json={"run_id": run_id, "comment": "confirmed"},
    )

    response = client.get(f"/api/review/events/event_danger?run_id={run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["event"]["event_id"] == "event_danger"
    assert payload["event"]["review_status"] == "confirmed"
    assert payload["review_state"]["status"] == "confirmed"
    assert payload["linked_alerts"][0]["alert_id"] == "alert_danger"
    assert payload["comments"][0]["comment"] == "confirmed"
    assert payload["visual_artifacts"]["keyframes"]["status"] == "available"
    assert payload["visual_artifacts"]["annotated_video"]["status"] == "available"


def test_confirm_false_positive_ignore_and_resolve_endpoints_write_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)

    confirm = client.post(
        "/api/review/events/event_danger/confirm",
        json={"run_id": run_id, "comment": "confirmed", "reviewer": "operator_1"},
    )
    false_positive = client.post(
        "/api/review/events/event_parking/false-positive",
        json={"run_id": run_id, "comment": "wrong zone"},
    )
    resolved_false_positive = client.post(
        "/api/review/events/event_parking/resolve",
        json={"run_id": run_id},
    )
    ignore = client.post(
        "/api/review/events/event_danger_2/ignore",
        json={"run_id": run_id},
    )
    resolved_ignored = client.post(
        "/api/review/events/event_danger_2/resolve",
        json={"run_id": run_id},
    )

    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    assert confirm.json()["review"]["after_status"] == "confirmed"
    assert confirm.json()["state"]["reviewer"] == "operator_1"
    assert false_positive.status_code == 200
    assert false_positive.json()["status"] == "false_positive"
    assert resolved_false_positive.status_code == 200
    assert resolved_false_positive.json()["status"] == "resolved"
    assert ignore.status_code == 200
    assert ignore.json()["status"] == "ignored"
    assert resolved_ignored.status_code == 200
    assert resolved_ignored.json()["status"] == "resolved"


def test_comment_endpoint_preserves_status_and_comments_can_be_listed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)
    client.post("/api/review/events/event_danger/confirm", json={"run_id": run_id})

    comment = client.post(
        "/api/review/comments",
        json={
            "run_id": run_id,
            "event_id": "event_danger",
            "comment": "second note",
            "reviewer": "reviewer_2",
        },
    )
    comments = client.get(f"/api/review/comments?run_id={run_id}&event_id=event_danger")

    assert comment.status_code == 200
    assert comment.json()["status"] == "confirmed"
    assert comment.json()["state"]["comment_count"] == 2
    assert comments.status_code == 200
    assert comments.json()["total"] == 2
    assert [item["action"] for item in comments.json()["items"]] == [
        "confirm",
        "comment",
    ]
    assert comments.json()["items"][1]["comment"] == "second note"


def test_false_negative_endpoint_writes_review_mvp_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)

    response = client.post(
        "/api/review/false-negatives",
        json={
            "run_id": run_id,
            "expected_event_type": "wrong_way_driving",
            "zone_id": None,
            "track_id": None,
            "start_frame": 100,
            "end_frame": 150,
            "start_time_ms": 3000,
            "end_time_ms": 5000,
            "description": "missed event",
            "reviewer": "reviewer_1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "false_negative"
    assert payload["false_negative"]["false_negative_id"].startswith("fn_")
    assert payload["false_negative"]["track_id"] is None
    assert payload["review"]["action"] == "add_false_negative"


def test_review_api_missing_run_and_event_return_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)

    missing_run = client.get("/api/review/events?run_id=missing_run")
    missing_event = client.get(f"/api/review/events/missing_event?run_id={run_id}")
    missing_action = client.post(
        "/api/review/events/missing_event/confirm",
        json={"run_id": run_id},
    )

    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "analysis run not found"
    assert missing_event.status_code == 404
    assert missing_event.json()["detail"] == "event not found"
    assert missing_action.status_code == 404
    assert missing_action.json()["detail"] == "event not found"


def test_review_api_invalid_transition_returns_400(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)
    client.post("/api/review/events/event_danger/confirm", json={"run_id": run_id})

    response = client.post(
        "/api/review/events/event_danger/false-positive",
        json={"run_id": run_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cannot apply mark_false_positive from confirmed"


def test_review_comments_missing_file_returns_empty_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)

    response = client.get(f"/api/review/comments?run_id={run_id}")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run_id,
        "event_id": None,
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
    }


def test_review_events_missing_event_artifact_returns_empty_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = "run_without_events"
    run_dir = tmp_path / "results" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": run_id, "video_id": "video_001", "artifacts": {}}),
        encoding="utf-8",
    )

    response = client.get(f"/api/review/events?run_id={run_id}")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_review_api_malformed_review_artifact_returns_clear_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_id = _create_review_run(tmp_path)
    (tmp_path / "results" / run_id / "event_review_state.json").write_text(
        "{bad json",
        encoding="utf-8",
    )

    response = client.get(f"/api/review/events?run_id={run_id}")

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid review artifact"


def _client_for_tmp_results(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_review_run(
    tmp_path: Path,
    *,
    with_visual_artifacts: bool = False,
) -> str:
    run_id = "run_stage7c"
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
            _event(
                run_id=run_id,
                event_id="event_danger",
                event_type="danger_zone_intrusion",
                severity="high",
            ),
            _event(
                run_id=run_id,
                event_id="event_parking",
                event_type="illegal_parking",
                severity="medium",
            ),
            _event(
                run_id=run_id,
                event_id="event_danger_2",
                event_type="danger_zone_intrusion",
                severity="low",
            ),
        ],
        event_evidence=[
            {
                "evidence_id": "evidence_danger",
                "event_id": "event_danger",
                "event_type": "danger_zone_intrusion",
                "evidence_type": "trajectory_window",
                "frame_index": 10,
                "timestamp_ms": 1000,
            }
        ],
        rule_executions=[{"event_id": "event_danger", "rule_id": "rule_001"}],
    )
    writer.write_alert_outputs(
        run_id=run_id,
        video_id="video_001",
        alerts=[
            {
                "id": "alert_danger",
                "alert_id": "alert_danger",
                "event_id": "event_danger",
                "video_id": "video_001",
                "run_id": run_id,
                "alert_type": "danger_zone_intrusion",
                "title": "Danger zone intrusion",
                "message": "Danger event",
                "level": "critical",
                "status": "new",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )
    if with_visual_artifacts:
        keyframes_dir = tmp_path / "results" / run_id / "keyframes"
        keyframes_dir.mkdir(exist_ok=True)
        (keyframes_dir / "index.json").write_text(
            json.dumps(
                {
                    "status": "available",
                    "items": [
                        {
                            "source_id": "event_danger",
                            "source_type": "event",
                            "path": "keyframes/event_danger.jpg",
                            "status": "available",
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "results" / run_id / "annotated_video.mp4").write_bytes(b"video")
    writer.write_run_manifest(run_id, status="completed")
    return run_id


def _event(
    *,
    run_id: str,
    event_id: str,
    event_type: str,
    severity: str,
) -> dict:
    return {
        "event_id": event_id,
        "run_id": run_id,
        "video_id": "video_001",
        "event_type": event_type,
        "severity": severity,
        "track_id": 17,
        "class_name": "car",
        "zone_id": "zone_001",
        "rule_id": "rule_001",
        "start_frame": 10,
        "end_frame": 12,
        "start_time_ms": 900,
        "end_time_ms": 1000,
        "confidence": 1.0,
        "status": "pending",
        "evidence": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }
