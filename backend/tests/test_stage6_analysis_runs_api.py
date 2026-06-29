from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_analysis_runs_list_discovers_manifest_backed_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    writer = TrafficArtifactWriter(tmp_path / "results")
    run_id = _create_manifest_backed_run(writer)

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1

    item = payload["items"][0]
    assert item["id"] == run_id
    assert item["run_id"] == run_id
    assert item["schema_version"] == "stage6d.v1"
    assert item["source"] == "manifest"
    assert item["video_id"] == "video_001"
    assert item["status"] == "completed"
    assert item["result_dir"] == f"results/traffic_analysis/{run_id}"
    assert item["metadata"] == {
        "available": True,
        "path": "metadata.json",
        "status": "available",
    }
    assert item["manifest"]["available"] is True
    assert item["manifest"]["path"] == "manifest.json"
    assert item["manifest"]["schema_version"] == "stage6b.v1"
    assert item["artifact_index"] == {
        "available": True,
        "path": "artifact_index.json",
        "status": "available",
    }
    assert item["artifact_summary"]["detections_csv"] == {
        "status": "available",
        "path": "detections.csv",
        "record_count": 1,
    }


def test_analysis_runs_list_discovers_metadata_backed_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    _write_metadata_backed_run(
        tmp_path / "results",
        run_id="run_metadata",
        video_id="video_metadata",
        status="completed",
        updated_at="2026-01-02T00:00:00+00:00",
    )

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["run_id"] == "run_metadata"
    assert item["source"] == "metadata"
    assert item["video_id"] == "video_metadata"
    assert item["metadata"]["status"] == "available"
    assert item["manifest"]["status"] == "missing"
    assert item["artifact_summary"]["events_jsonl"] == {
        "status": "empty",
        "path": "events.jsonl",
        "record_count": 0,
    }


def test_analysis_runs_list_discovers_artifact_index_backed_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_dir = tmp_path / "results" / "run_index"
    run_dir.mkdir(parents=True)
    (run_dir / "artifact_index.json").write_text(
        json.dumps(
            {
                "schema_version": "stage6b.v1",
                "run_id": "run_index",
                "video_id": "video_index",
                "result_dir": "results/traffic_analysis/run_index",
                "artifacts": {"detections_csv": "detections.csv"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["run_id"] == "run_index"
    assert item["source"] == "artifact_index"
    assert item["video_id"] == "video_index"
    assert item["artifact_index"]["status"] == "available"
    assert item["artifact_paths"] == {"detections_csv": "detections.csv"}


def test_analysis_runs_list_treats_manifest_available_true_as_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    run_dir = tmp_path / "results" / "run_available_manifest"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "run_available_manifest",
                "video_id": "video_available",
                "status": "completed",
                "artifacts": {
                    "detections_csv": {
                        "available": True,
                        "path": "detections.csv",
                        "record_count": 0,
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["artifact_summary"]["detections_csv"]["status"] == "available"


def test_analysis_runs_list_discovers_directory_scan_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    (tmp_path / "results" / "run_directory_only").mkdir(parents=True)

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["run_id"] == "run_directory_only"
    assert item["source"] == "directory_scan"
    assert item["metadata"]["status"] == "missing"
    assert item["manifest"]["status"] == "missing"
    assert item["artifact_index"]["status"] == "missing"
    assert item["artifact_summary"] == {}


def test_analysis_runs_list_deduplicates_registry_and_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    writer = TrafficArtifactWriter(tmp_path / "results")
    run_id = _create_manifest_backed_run(writer)
    traffic_analysis_service.register_run(
        run_id=run_id,
        video_id="video_registry",
        result_dir=f"results/traffic_analysis/{run_id}",
        artifact_index={"metadata": "metadata.json"},
    )

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["source"] == "manifest"
    assert payload["items"][0]["video_id"] == "video_001"


def test_analysis_runs_list_filters_and_paginates_with_stable_sort(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    results_dir = tmp_path / "results"
    _write_metadata_backed_run(
        results_dir,
        run_id="run_old",
        video_id="video_a",
        status="completed",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    _write_metadata_backed_run(
        results_dir,
        run_id="run_mid",
        video_id="video_a",
        status="failed",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    _write_metadata_backed_run(
        results_dir,
        run_id="run_new",
        video_id="video_b",
        status="completed",
        updated_at="2026-01-03T00:00:00+00:00",
    )

    page_response = client.get("/api/analysis-runs?limit=2&offset=1")
    status_response = client.get("/api/analysis-runs?status=completed")
    video_response = client.get("/api/analysis-runs?video_id=video_a")

    assert page_response.status_code == 200
    assert [item["run_id"] for item in page_response.json()["items"]] == [
        "run_mid",
        "run_old",
    ]
    assert status_response.json()["total"] == 2
    assert [item["run_id"] for item in status_response.json()["items"]] == [
        "run_new",
        "run_old",
    ]
    assert video_response.json()["total"] == 2
    assert [item["run_id"] for item in video_response.json()["items"]] == [
        "run_mid",
        "run_old",
    ]


def test_analysis_run_summary_endpoint_returns_unified_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    writer = TrafficArtifactWriter(tmp_path / "results")
    run_id = _create_manifest_backed_run(writer)

    response = client.get(f"/api/analysis-runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["id"] == run_id
    assert payload["schema_version"] == "stage6d.v1"
    assert payload["source"] == "manifest"
    assert payload["manifest"]["status"] == "available"
    assert payload["artifact_index"]["status"] == "available"
    assert payload["metadata"]["status"] == "available"
    assert payload["artifact_summary"]["metadata"]["status"] == "available"


def test_analysis_runs_list_survives_corrupt_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    _write_metadata_backed_run(
        tmp_path / "results",
        run_id="run_corrupt_manifest",
        video_id="video_corrupt",
        status="completed",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    (tmp_path / "results" / "run_corrupt_manifest" / "manifest.json").write_text(
        "{bad json",
        encoding="utf-8",
    )

    response = client.get("/api/analysis-runs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["run_id"] == "run_corrupt_manifest"
    assert item["source"] == "metadata"
    assert item["manifest"]["status"] == "error"
    assert item["manifest"]["available"] is False


def test_analysis_run_summary_missing_run_returns_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)

    response = client.get("/api/analysis-runs/missing_run")

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


def _create_manifest_backed_run(writer: TrafficArtifactWriter) -> str:
    run_id = "run_stage6d_manifest"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "mode": "offline",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00+00:00",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:01:00+00:00",
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
        ],
    )
    writer.write_run_manifest(run_id, status="completed")
    return run_id


def _write_metadata_backed_run(
    results_dir: Path,
    *,
    run_id: str,
    video_id: str,
    status: str,
    updated_at: str,
) -> None:
    run_dir = results_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": video_id,
                "status": status,
                "mode": "offline",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": updated_at,
                "result_dir": f"results/traffic_analysis/{run_id}",
                "artifact_summary": {
                    "events_jsonl": {
                        "status": "empty",
                        "path": "events.jsonl",
                        "record_count": 0,
                    }
                },
                "artifacts": {"events_jsonl": "events.jsonl"},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
