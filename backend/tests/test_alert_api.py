from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_alert_api_generate_alerts(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path)

    response = client.post(f"/api/analysis-runs/{run_id}/alerts/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["video_id"] == "video_001"
    assert payload["status"] == "completed"
    assert payload["total_alerts"] == 2
    assert payload["alert_summary"]["per_level_counts"] == {
        "critical": 1,
        "warning": 1,
    }
    assert payload["artifacts"]["alerts"] == "alerts.jsonl"


def test_alert_api_get_alerts(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path)
    client.post(f"/api/analysis-runs/{run_id}/alerts/generate")

    response = client.get(f"/api/analysis-runs/{run_id}/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["summary"]["total_alerts"] == 2
    assert len(payload["alerts"]) == 2
    assert payload["limit"] == 100
    assert payload["status"] is None
    assert payload["level"] is None
    assert payload["event_type"] is None


def test_alert_api_limit_zero(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path)
    client.post(f"/api/analysis-runs/{run_id}/alerts/generate")

    response = client.get(f"/api/analysis-runs/{run_id}/alerts?limit=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_alerts"] == 2
    assert payload["alerts"] == []


def test_alert_api_filters(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path)
    client.post(f"/api/analysis-runs/{run_id}/alerts/generate")

    response = client.get(
        f"/api/analysis-runs/{run_id}/alerts?level=critical&event_type=danger_zone_intrusion&status=new"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "critical"
    assert payload["event_type"] == "danger_zone_intrusion"
    assert payload["status"] == "new"
    assert [alert["event_type"] for alert in payload["alerts"]] == [
        "danger_zone_intrusion"
    ]


def test_alert_api_missing_run(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)

    response = client.get("/api/analysis-runs/missing_run/alerts")

    assert response.status_code == 404


def test_alert_api_missing_alert_artifacts(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_event_artifact_run(tmp_path)

    response = client.get(f"/api/analysis-runs/{run_id}/alerts")

    assert response.status_code == 404


def test_alert_api_generate_missing_events_artifacts(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = "run_without_events"
    run_dir = tmp_path / "results" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        '{"run_id":"run_without_events","video_id":"video_001","artifacts":{}}\n',
        encoding="utf-8",
    )

    response = client.post(f"/api/analysis-runs/{run_id}/alerts/generate")

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


def _create_event_artifact_run(tmp_path: Path) -> str:
    run_id = "run_with_events"
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "stage": "stage_4_trajectory_engine",
            "artifacts": {
                "trajectory_points_jsonl": "trajectory_points.jsonl",
                "trajectory_summary": "trajectory_summary.json",
            },
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            _event(
                event_id="event_danger",
                event_type="danger_zone_intrusion",
                severity="high",
            ),
            _event(
                event_id="event_parking",
                event_type="illegal_parking",
                severity="medium",
            ),
        ],
        event_evidence=[],
        rule_executions=[],
    )
    return run_id


def _event(*, event_id: str, event_type: str, severity: str) -> dict:
    return {
        "event_id": event_id,
        "run_id": "run_with_events",
        "video_id": "video_001",
        "event_type": event_type,
        "severity": severity,
        "track_id": 7,
        "class_name": "car",
        "zone_id": "zone_001",
        "rule_id": "rule_001",
        "start_frame": 10,
        "end_frame": 10,
        "start_time_ms": 1000,
        "end_time_ms": 1000,
        "confidence": 1.0,
        "status": "pending",
        "evidence": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }
