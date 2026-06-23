from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_event_api_get_events(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path, video_id="video_001")

    response = client.get(f"/api/analysis-runs/{run_id}/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["video_id"] == "video_001"
    assert payload["summary"]["total_events"] == 2
    assert len(payload["events"]) == 2
    assert len(payload["event_evidence"]) == 2
    assert len(payload["rule_executions"]) == 2
    assert payload["limit"] == 100
    assert payload["event_type"] is None
    assert payload["track_id"] is None


def test_event_api_limit(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path, video_id="video_001")

    response = client.get(f"/api/analysis-runs/{run_id}/events?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert len(payload["events"]) == 1
    assert len(payload["event_evidence"]) == 1
    assert len(payload["rule_executions"]) == 1


def test_event_api_limit_zero(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path, video_id="video_001")

    response = client.get(f"/api/analysis-runs/{run_id}/events?limit=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_events"] == 2
    assert payload["events"] == []
    assert payload["event_evidence"] == []
    assert payload["rule_executions"] == []


def test_event_api_event_type_filter(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path, video_id="video_001")

    response = client.get(
        f"/api/analysis-runs/{run_id}/events?event_type=illegal_parking"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_type"] == "illegal_parking"
    assert [event["event_type"] for event in payload["events"]] == [
        "illegal_parking"
    ]
    assert [evidence["event_id"] for evidence in payload["event_evidence"]] == [
        "event_parking"
    ]
    assert [execution["event_id"] for execution in payload["rule_executions"]] == [
        "event_parking"
    ]


def test_event_api_track_id_filter(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path, video_id="video_001")

    response = client.get(f"/api/analysis-runs/{run_id}/events?track_id=8")

    assert response.status_code == 200
    payload = response.json()
    assert payload["track_id"] == 8
    assert [event["track_id"] for event in payload["events"]] == [8]
    assert [evidence["track_id"] for evidence in payload["event_evidence"]] == [8]
    assert [execution["track_id"] for execution in payload["rule_executions"]] == [8]


def test_event_api_missing_run(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)

    response = client.get("/api/analysis-runs/missing_run/events")

    assert response.status_code == 404


def test_event_api_missing_event_artifacts(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = "run_without_events"
    run_dir = tmp_path / "results" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        '{"run_id":"run_without_events","video_id":"video_001","artifacts":{}}\n',
        encoding="utf-8",
    )

    response = client.get(f"/api/analysis-runs/{run_id}/events")

    assert response.status_code == 404


def _client_for_tmp_run(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_event_artifact_run(tmp_path: Path, video_id: str) -> str:
    run_id = "run_with_events"
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(
        run_id,
        {
            "video_id": video_id,
            "stage": "stage_4_trajectory_engine",
            "artifacts": {
                "trajectory_points_jsonl": "trajectory_points.jsonl",
                "trajectory_summary": "trajectory_summary.json",
            },
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id=video_id,
        events=[
            _event(
                event_id="event_danger",
                event_type="danger_zone_intrusion",
                track_id=7,
                rule_id="rule_danger",
            ),
            _event(
                event_id="event_parking",
                event_type="illegal_parking",
                track_id=8,
                rule_id="rule_parking",
            ),
        ],
        event_evidence=[
            _evidence(event_id="event_danger", track_id=7),
            _evidence(event_id="event_parking", track_id=8),
        ],
        rule_executions=[
            _execution(event_id="event_danger", track_id=7, rule_id="rule_danger"),
            _execution(event_id="event_parking", track_id=8, rule_id="rule_parking"),
        ],
    )
    return run_id


def _event(
    *,
    event_id: str,
    event_type: str,
    track_id: int,
    rule_id: str,
) -> dict:
    return {
        "event_id": event_id,
        "run_id": "run_with_events",
        "video_id": "video_001",
        "event_type": event_type,
        "severity": "medium",
        "track_id": track_id,
        "class_name": "car",
        "zone_id": "zone_001",
        "rule_id": rule_id,
        "start_frame": 10,
        "end_frame": 10,
        "start_time_ms": 1000,
        "end_time_ms": 1000,
        "confidence": 1.0,
        "status": "pending",
        "evidence": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _evidence(*, event_id: str, track_id: int) -> dict:
    return {
        "evidence_id": f"evidence_{event_id}",
        "event_id": event_id,
        "run_id": "run_with_events",
        "video_id": "video_001",
        "track_id": track_id,
        "frame_index": 10,
        "timestamp_ms": 1000,
        "evidence_type": "zone",
        "evidence_json": {},
        "snapshot_path": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _execution(*, event_id: str, track_id: int, rule_id: str) -> dict:
    return {
        "execution_id": f"execution_{event_id}",
        "run_id": "run_with_events",
        "rule_id": rule_id,
        "event_id": event_id,
        "track_id": track_id,
        "frame_index": 10,
        "status": "matched",
        "input_features": {},
        "output_result": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }
