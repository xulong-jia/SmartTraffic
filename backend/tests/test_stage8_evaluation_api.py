import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_evaluation_api_list_register_run_results_summary_and_failed_cases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    run_id = _create_api_run(tmp_path)
    _write_expected_events(tmp_path)

    empty_datasets = client.get("/api/evaluation/datasets")
    registered = client.post(
        "/api/evaluation/datasets",
        json={
            "dataset_id": "dataset_api",
            "name": "API Dataset",
            "dataset_type": "event",
            "expected_events_path": "expected/events.json",
        },
    )
    datasets = client.get("/api/evaluation/datasets")
    run_response = client.post(
        "/api/evaluation/run",
        json={"run_id": run_id, "dataset_id": "dataset_api", "evaluation_type": "event"},
    )
    runs = client.get(f"/api/evaluation/runs?run_id={run_id}")
    results = client.get(f"/api/evaluation/results?run_id={run_id}&evaluation_type=event")
    summary = client.get(f"/api/evaluation/summary/{run_id}")
    failed_cases = client.get(f"/api/evaluation/failed-cases?run_id={run_id}")

    assert empty_datasets.status_code == 200
    assert empty_datasets.json()["datasets"] == []
    assert registered.status_code == 200
    assert registered.json()["dataset_id"] == "dataset_api"
    assert datasets.json()["datasets"][0]["dataset_id"] == "dataset_api"
    assert run_response.status_code == 200
    assert run_response.json()["evaluation_run"]["status"] == "completed"
    assert runs.status_code == 200
    assert runs.json()["items"][0]["run_id"] == run_id
    assert results.status_code == 200
    assert any(item["metric_name"] == "event_precision" for item in results.json()["items"])
    assert summary.status_code == 200
    assert summary.json()["run_id"] == run_id
    assert summary.json()["summary"]["bad_case_regression"]["status"] == "planned"
    assert failed_cases.status_code == 200
    assert any(item["failure_type"] == "false_positive" for item in failed_cases.json()["items"])


def test_evaluation_api_missing_run_and_dataset_return_clear_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    run_id = _create_api_run(tmp_path)

    missing_run = client.post(
        "/api/evaluation/run",
        json={"run_id": "missing_run", "evaluation_type": "event"},
    )
    missing_dataset = client.post(
        "/api/evaluation/run",
        json={"run_id": run_id, "dataset_id": "missing_dataset", "evaluation_type": "event"},
    )

    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "analysis run not found"
    assert missing_dataset.status_code == 404
    assert missing_dataset.json()["detail"] == "evaluation dataset not found"


def test_run_evals_cli_smoke_outputs_json(tmp_path: Path) -> None:
    run_id = _create_cli_run(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--run-id",
            run_id,
            "--evaluation-type",
            "trajectory",
            "--results-root",
            str(tmp_path / "results"),
            "--eval-root",
            str(tmp_path / "evals"),
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["evaluation_run"]["run_id"] == run_id
    assert payload["evaluation_run"]["evaluation_type"] == "trajectory"
    assert payload["summary"]["summary"]["bad_case_regression"]["status"] == "planned"


def _client_for_tmp_evaluation(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("SMARTTRAFFIC_EVALS_DIR", str(tmp_path / "evals"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_api_run(tmp_path: Path) -> str:
    run_id = "run_eval_api"
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(run_id, {"video_id": "video_001", "status": "completed"})
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            {"event_id": "actual_1", "run_id": run_id, "video_id": "video_001", "event_type": "wrong_way_driving", "start_frame": 12, "end_frame": 18}
        ],
        event_evidence=[],
        rule_executions=[],
    )
    writer.write_run_manifest(run_id, status="completed")
    return run_id


def _create_cli_run(tmp_path: Path) -> str:
    run_id = "run_eval_cli"
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(run_id, {"video_id": "video_001", "status": "completed"})
    writer.write_trajectory_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 1,
                "timestamp_ms": 100,
                "trajectory_points": [
                    {"track_id": 1, "class_id": 2, "class_name": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10], "center": [5, 5], "bottom_center": [5, 10], "state": "confirmed", "track_length": 1, "speed_px_per_second": 12, "moving_angle": 90}
                ],
            }
        ],
    )
    return run_id


def _write_expected_events(tmp_path: Path) -> None:
    expected_path = tmp_path / "evals" / "expected" / "events.json"
    expected_path.parent.mkdir(parents=True)
    expected_path.write_text(
        json.dumps({"events": [{"event_id": "expected_1", "event_type": "illegal_parking", "start_frame": 40, "end_frame": 50}]}),
        encoding="utf-8",
    )
