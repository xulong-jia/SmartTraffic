import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.bad_case_service import BadCaseService
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
    assert summary.json()["summary"]["bad_case_regression"]["status"] == "empty"
    assert failed_cases.status_code == 200
    assert any(item["failure_type"] == "false_positive" for item in failed_cases.json()["items"])


def test_evaluation_api_uses_run_expected_events_without_dataset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    run_id = _create_api_run(tmp_path)
    _write_run_expected_events(tmp_path, run_id)

    run_response = client.post(
        "/api/evaluation/run",
        json={"run_id": run_id, "evaluation_type": "event"},
    )

    assert run_response.status_code == 200
    results = {
        item["metric_name"]: item
        for item in run_response.json()["results"]
    }
    assert results["event_precision"]["metric_value"] == 1.0
    assert results["event_recall"]["metric_value"] == 1.0
    assert results["event_f1"]["metric_value"] == 1.0
    assert results["false_alarm_rate"]["metric_value"] == 0.0
    assert results["event_precision"]["details"]["status"] == "available"


def test_evaluation_api_adhoc_event_dataset_uses_run_expected_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    run_id = _create_api_run(tmp_path)
    _write_run_expected_events(tmp_path, run_id)

    run_response = client.post(
        "/api/evaluation/run",
        json={
            "run_id": run_id,
            "dataset_id": "adhoc-event",
            "evaluation_type": "event",
        },
    )

    assert run_response.status_code == 200
    payload = run_response.json()
    results = {item["metric_name"]: item for item in payload["results"]}
    assert payload["evaluation_run"]["dataset_id"] == "adhoc-event"
    assert results["event_accuracy"]["metric_value"] == 1.0
    assert results["event_precision"]["metric_value"] == 1.0
    assert results["event_recall"]["metric_value"] == 1.0
    assert results["event_f1"]["metric_value"] == 1.0
    assert results["false_alarm_rate"]["metric_value"] == 0.0
    assert results["event_precision"]["details"]["status"] == "available"
    assert results["event_precision"]["details"]["event_count_expected"] == 1
    assert results["event_precision"]["details"]["event_count_actual"] == 1
    assert results["event_precision"]["details"]["true_positive"] == 1
    datasets = client.get("/api/evaluation/datasets")
    adhoc_dataset = next(
        dataset
        for dataset in datasets.json()["datasets"]
        if dataset["dataset_id"] == "adhoc-event"
    )
    assert adhoc_dataset["source"] == "ad_hoc"


def test_evaluation_api_adhoc_event_dataset_falls_back_from_empty_expected_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    events = _demo_danger_zone_events()
    run_id = _create_api_run_with_events(tmp_path, "run_50007c86fd60", events)
    _write_dataset_expected_events(tmp_path, [])
    _write_run_expected_events(tmp_path, run_id, events=events)

    registered = client.post(
        "/api/evaluation/datasets",
        json={
            "dataset_id": "adhoc-event",
            "name": "Ad hoc Event",
            "dataset_type": "event",
            "expected_events_path": "expected/events.json",
        },
    )
    run_response = client.post(
        "/api/evaluation/run",
        json={
            "run_id": run_id,
            "dataset_id": "adhoc-event",
            "evaluation_type": "event",
        },
    )

    assert registered.status_code == 200
    assert run_response.status_code == 200
    results = {item["metric_name"]: item for item in run_response.json()["results"]}
    precision = results["event_precision"]
    assert precision["metric_value"] == 1.0
    assert precision["details"]["status"] == "available"
    assert precision["details"].get("reason") != "missing expected events"
    assert precision["details"]["event_count_expected"] == 14
    assert precision["details"]["event_count_actual"] == 14
    assert precision["details"]["true_positive"] == 14
    assert precision["details"]["false_positive"] == 0
    assert precision["details"]["false_negative"] == 0
    assert results["event_accuracy"]["metric_value"] == 1.0
    assert results["event_recall"]["metric_value"] == 1.0
    assert results["event_f1"]["metric_value"] == 1.0
    assert results["false_alarm_rate"]["metric_value"] == 0.0


def test_evaluation_api_dataset_without_expected_events_stays_not_applicable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_evaluation(tmp_path, monkeypatch)
    run_id = _create_api_run(tmp_path)

    registered = client.post(
        "/api/evaluation/datasets",
        json={
            "dataset_id": "dataset_without_expected",
            "name": "Dataset without expected events",
            "dataset_type": "event",
        },
    )
    run_response = client.post(
        "/api/evaluation/run",
        json={
            "run_id": run_id,
            "dataset_id": "dataset_without_expected",
            "evaluation_type": "event",
        },
    )

    assert registered.status_code == 200
    assert run_response.status_code == 200
    result = next(
        item
        for item in run_response.json()["results"]
        if item["metric_name"] == "event_precision"
    )
    assert result["metric_value"] is None
    assert result["details"]["status"] == "not_applicable"
    assert result["details"]["reason"] == "missing expected events"


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
    bad_case_service = BadCaseService(
        artifact_writer=TrafficArtifactWriter(tmp_path / "results")
    )
    bad_case_service.create_bad_case(
        run_id=run_id,
        record={
            "case_type": "false_negative",
            "module": "event_engine",
            "description": "Regression smoke case.",
            "source": "evaluation_center",
            "linked_failed_case_id": "failed_cli",
        },
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--run-id",
            run_id,
            "--evaluation-type",
            "regression",
            "--results-root",
            str(tmp_path / "results"),
            "--eval-root",
            str(tmp_path / "evals"),
            "--case-type",
            "false_negative",
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["evaluation_run"]["run_id"] == run_id
    assert payload["evaluation_run"]["evaluation_type"] == "regression"
    regression = payload["summary"]["summary"]["bad_case_regression"]
    assert regression["status"] == "insufficient_data"
    assert regression["total_cases"] == 1


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
    return _create_api_run_with_events(
        tmp_path,
        run_id,
        [
            {
                "event_id": "actual_1",
                "run_id": run_id,
                "video_id": "video_001",
                "event_type": "wrong_way_driving",
                "start_frame": 12,
                "end_frame": 18,
            }
        ],
    )


def _create_api_run_with_events(
    tmp_path: Path,
    run_id: str,
    events: list[dict[str, object]],
) -> str:
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(run_id, {"video_id": "video_001", "status": "completed"})
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=events,
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
    _write_dataset_expected_events(
        tmp_path,
        [
            {
                "event_id": "expected_1",
                "event_type": "illegal_parking",
                "start_frame": 40,
                "end_frame": 50,
            }
        ],
    )


def _write_dataset_expected_events(
    tmp_path: Path,
    events: list[dict[str, object]],
) -> None:
    expected_path = tmp_path / "evals" / "expected" / "events.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(
        json.dumps({"events": events}),
        encoding="utf-8",
    )


def _write_run_expected_events(
    tmp_path: Path,
    run_id: str,
    *,
    events: list[dict[str, object]] | None = None,
) -> None:
    expected_events = events
    if expected_events is None:
        expected_events = [
            {
                "event_id": "expected_1",
                "event_type": "wrong_way_driving",
                "start_frame": 12,
                "end_frame": 18,
            }
        ]
    expected_path = tmp_path / "evals" / "expected" / f"{run_id}_expected_events.json"
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(
        json.dumps({"run_id": run_id, "events": _expected_events(expected_events)}),
        encoding="utf-8",
    )


def _expected_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            **event,
            "event_id": f"expected_event_{index:03d}",
        }
        for index, event in enumerate(events, start=1)
    ]


def _demo_danger_zone_events() -> list[dict[str, object]]:
    track_frames = [
        (2, 0),
        (4, 0),
        (6, 0),
        (7, 0),
        (11, 0),
        (16, 0),
        (17, 0),
        (18, 0),
        (24, 0),
        (30, 0),
        (41, 27),
        (63, 54),
        (8, 75),
        (73, 83),
    ]
    return [
        {
            "event_id": f"actual_event_{index:03d}",
            "run_id": "run_50007c86fd60",
            "video_id": "video_001",
            "event_type": "danger_zone_intrusion",
            "track_id": track_id,
            "zone_id": "zone_b64fa50a13e4",
            "start_frame": frame,
            "end_frame": frame,
            "severity": "medium",
        }
        for index, (track_id, frame) in enumerate(track_frames, start=1)
    ]
