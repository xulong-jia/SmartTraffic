import csv
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_stage6_manifest_and_artifact_index_are_written(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = _create_complete_run(writer)

    manifest = writer.write_run_manifest(run_id, status="completed")

    run_dir = tmp_path / run_id
    manifest_path = run_dir / "manifest.json"
    artifact_index_path = run_dir / "artifact_index.json"
    metadata_path = run_dir / "metadata.json"
    artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert manifest_path.is_file()
    assert artifact_index_path.is_file()
    assert manifest["schema_version"] == "stage6b.v1"
    assert manifest["run_id"] == run_id
    assert manifest["video_id"] == "video_001"
    assert manifest["status"] == "completed"
    assert manifest["result_dir"] == f"results/traffic_analysis/{run_id}"

    artifacts = manifest["artifacts"]
    assert artifacts["metadata"] == {
        "status": "available",
        "path": "metadata.json",
        "format": "json",
        "record_count": 1,
        "required": True,
    }
    assert artifacts["detections_csv"]["status"] == "available"
    assert artifacts["detections_csv"]["record_count"] == 1
    assert artifacts["detections_jsonl"]["record_count"] == 2
    assert artifacts["tracks_csv"]["status"] == "available"
    assert artifacts["tracks_csv"]["record_count"] == 1
    assert artifacts["trajectory_points_csv"]["record_count"] == 3
    assert artifacts["events_jsonl"]["record_count"] == 2
    assert artifacts["event_evidence_jsonl"]["record_count"] == 1
    assert artifacts["rule_executions_jsonl"]["record_count"] == 2
    assert artifacts["alerts_jsonl"]["record_count"] == 1

    for key in (
        "flow_counts",
        "zone_statistics",
        "evaluation_summary",
    ):
        assert artifacts[key]["status"] == "planned"
        assert artifacts[key]["record_count"] == 0
        assert artifacts[key]["required"] is False
    assert artifacts["keyframes"]["status"] == "empty"
    assert artifacts["keyframes"]["record_count"] == 0
    assert artifacts["keyframes_index"]["status"] == "missing"
    assert artifacts["annotated_video"]["status"] == "missing"
    assert artifacts["annotated_video"]["record_count"] == 0

    assert artifact_index == {
        "schema_version": "stage6b.v1",
        "run_id": run_id,
        "video_id": "video_001",
        "result_dir": f"results/traffic_analysis/{run_id}",
        "artifacts": {
            "metadata": "metadata.json",
            "manifest": "manifest.json",
            "artifact_index": "artifact_index.json",
            "detections_csv": "detections.csv",
            "detections_jsonl": "detections.jsonl",
            "detection_summary": "detection_summary.json",
            "tracks_csv": "tracks.csv",
            "tracks_jsonl": "tracks.jsonl",
            "tracking_summary": "tracking_summary.json",
            "trajectory_points_csv": "trajectory_points.csv",
            "trajectory_points_jsonl": "trajectory_points.jsonl",
            "trajectory_summary": "trajectory_summary.json",
            "events_jsonl": "events.jsonl",
            "event_evidence_jsonl": "event_evidence.jsonl",
            "rule_executions_jsonl": "rule_executions.jsonl",
            "event_summary": "event_summary.json",
            "alerts_jsonl": "alerts.jsonl",
            "alert_summary": "alert_summary.json",
            "flow_counts": "flow_counts.json",
            "zone_statistics": "zone_statistics.json",
            "evaluation_summary": "evaluation_summary.json",
            "keyframes": "keyframes/",
        },
    }
    assert metadata["schema_version"] == "stage6b.v1"
    assert metadata["status"] == "completed"
    assert metadata["result_dir"] == f"results/traffic_analysis/{run_id}"
    assert metadata["manifest_path"] == "manifest.json"
    assert metadata["artifact_index_path"] == "artifact_index.json"
    assert metadata["artifact_summary"]["detections_csv"] == {
        "status": "available",
        "path": "detections.csv",
        "record_count": 1,
    }


def test_stage6_manifest_marks_missing_core_and_planned_future_artifacts(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(
        "run_missing_core",
        {"video_id": "video_001", "mode": "offline"},
    )

    manifest = writer.write_run_manifest("run_missing_core")

    artifacts = manifest["artifacts"]
    assert artifacts["detections_csv"]["status"] == "missing"
    assert artifacts["tracks_csv"]["status"] == "missing"
    assert artifacts["events_jsonl"]["status"] == "missing"
    assert artifacts["alerts_jsonl"]["status"] == "missing"
    assert artifacts["flow_counts"]["status"] == "planned"
    assert artifacts["zone_statistics"]["status"] == "planned"
    assert artifacts["evaluation_summary"]["status"] == "planned"
    assert artifacts["keyframes"]["status"] == "empty"
    assert artifacts["keyframes_index"]["status"] == "missing"
    assert artifacts["annotated_video"]["status"] == "missing"


def test_analysis_run_manifest_api_builds_and_returns_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    writer = TrafficArtifactWriter(tmp_path / "results")
    run_id = _create_complete_run(writer)

    response = client.get(f"/api/analysis-runs/{run_id}/manifest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "stage6b.v1"
    assert payload["run_id"] == run_id
    assert payload["artifacts"]["detections_csv"]["status"] == "available"
    assert payload["artifacts"]["flow_counts"]["status"] == "planned"
    assert (tmp_path / "results" / run_id / "manifest.json").is_file()
    assert (tmp_path / "results" / run_id / "artifact_index.json").is_file()


def test_analysis_run_manifest_api_missing_run_returns_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)

    response = client.get("/api/analysis-runs/missing_run/manifest")

    assert response.status_code == 404


def _client_for_tmp_results(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_complete_run(writer: TrafficArtifactWriter) -> str:
    run_id = "run_stage6b"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "mode": "offline",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:01:00+00:00",
            "detector_config": {"dry_run": True},
            "tracker_config": {"dry_run": True},
            "event_config": {"source": "test"},
        },
    )
    writer.write_detection_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.9,
                        "bbox": [1, 2, 30, 40],
                    }
                ],
            },
            {"frame_index": 1, "timestamp_ms": 100, "detections": []},
        ],
    )
    writer.write_tracking_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "tracks": [
                    {
                        "track_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.9,
                        "bbox": [1, 2, 30, 40],
                        "center": [15.5, 21.0],
                        "state": "confirmed",
                    }
                ],
            },
        ],
    )
    writer.write_trajectory_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "trajectory_points": [
                    {"track_id": 1, "class_name": "car", "bbox": [1, 2, 30, 40]},
                    {"track_id": 2, "class_name": "person", "bbox": [5, 6, 20, 30]},
                ],
            },
            {
                "frame_index": 1,
                "timestamp_ms": 100,
                "trajectory_points": [
                    {"track_id": 1, "class_name": "car", "bbox": [2, 3, 31, 41]},
                ],
            },
        ],
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[{"event_id": "event_1"}, {"event_id": "event_2"}],
        event_evidence=[{"event_id": "event_1", "evidence_id": "evidence_1"}],
        rule_executions=[{"event_id": "event_1"}, {"event_id": "event_2"}],
    )
    writer.write_alert_outputs(
        run_id=run_id,
        video_id="video_001",
        alerts=[{"alert_id": "alert_1", "status": "new"}],
    )
    _assert_csv_has_one_data_row(writer.base_dir / run_id / "detections.csv")
    return run_id


def _assert_csv_has_one_data_row(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as file:
        assert len(list(csv.DictReader(file))) == 1
