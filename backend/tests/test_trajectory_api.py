import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_trajectory_api_process_mode(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    video_id = _upload_video(client, tmp_path)

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking_trajectory",
            "detector_dry_run": True,
            "tracker_dry_run": True,
            "max_frames": 2,
            "direction_window": 2,
            "dwell_speed_threshold": 1.0,
            "max_history_points": 10,
        },
    )

    assert process_response.status_code == 200
    payload = process_response.json()
    assert payload["status"] == "completed"
    assert payload["stage"] == "stage_4_trajectory_engine"
    assert payload["next_stage"] == "stage_5_event_engine_not_started"
    assert "total_trajectory_points" in payload


def test_trajectory_api_get_trajectory_points(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    video_id = _upload_video(client, tmp_path)
    run_id = _run_trajectory_process(client, video_id)

    response = client.get(f"/api/analysis-runs/{run_id}/trajectory-points")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert "summary" in payload
    assert "frames" in payload
    assert "rows" in payload
    assert payload["limit"] == 100
    assert payload["track_id"] is None


def test_trajectory_api_limit(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")

    response = client.get(f"/api/analysis-runs/{run_id}/trajectory-points?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert len(payload["frames"]) <= 1
    assert len(payload["rows"]) <= 1


def test_trajectory_api_track_id_filter(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")

    response = client.get(
        f"/api/analysis-runs/{run_id}/trajectory-points?track_id=2&limit=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["track_id"] == 2
    assert {row["track_id"] for row in payload["rows"]} == {"2"}
    for frame in payload["frames"]:
        assert all(
            point["track_id"] == 2 for point in frame.get("trajectory_points", [])
        )


def test_trajectory_api_missing_run(tmp_path: Path, monkeypatch) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)

    response = client.get("/api/analysis-runs/missing_run/trajectory-points")

    assert response.status_code == 404


def test_trajectory_api_missing_trajectory_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    video_id = _upload_video(client, tmp_path)
    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking",
            "detector_dry_run": True,
            "tracker_dry_run": True,
            "max_frames": 1,
        },
    )
    assert process_response.status_code == 200
    run_id = process_response.json()["run_id"]

    response = client.get(f"/api/analysis-runs/{run_id}/trajectory-points")

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


def _upload_video(client: TestClient, tmp_path: Path) -> str:
    video_path = _make_video(tmp_path / "upload.mp4", frame_count=4)
    with video_path.open("rb") as file:
        response = client.post(
            "/api/videos/upload",
            files={"file": ("upload.mp4", file, "video/mp4")},
        )
    assert response.status_code == 200
    return response.json()["id"]


def _run_trajectory_process(client: TestClient, video_id: str) -> str:
    response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking_trajectory",
            "detector_dry_run": True,
            "tracker_dry_run": True,
            "max_frames": 2,
        },
    )
    assert response.status_code == 200
    return response.json()["run_id"]


def _create_trajectory_artifact_run(tmp_path: Path, video_id: str) -> str:
    run_id = "run_with_trajectory"
    run_dir = tmp_path / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "video_id": video_id,
        "stage": "stage_4_trajectory_engine",
        "artifacts": {
            "trajectory_points": "trajectory_points.csv",
            "trajectory_points_csv": "trajectory_points.csv",
            "trajectory_points_jsonl": "trajectory_points.jsonl",
            "trajectory_summary": "trajectory_summary.json",
        },
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "trajectory_summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": video_id,
                "total_frames_processed": 2,
                "total_trajectory_points": 3,
                "unique_track_ids": 2,
                "track_state_counts": {"confirmed": 3},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    frames = [
        {
            "run_id": run_id,
            "video_id": video_id,
            "frame_index": 0,
            "timestamp_ms": 0,
            "trajectory_points": [
                {"track_id": 1, "track_length": 1},
                {"track_id": 2, "track_length": 1},
            ],
        },
        {
            "run_id": run_id,
            "video_id": video_id,
            "frame_index": 1,
            "timestamp_ms": 100,
            "trajectory_points": [{"track_id": 2, "track_length": 2}],
        },
    ]
    (run_dir / "trajectory_points.jsonl").write_text(
        "".join(json.dumps(frame, ensure_ascii=False) + "\n" for frame in frames),
        encoding="utf-8",
    )
    (run_dir / "trajectory_points.csv").write_text(
        "\n".join(
            [
                "run_id,video_id,frame_index,timestamp_ms,track_id,track_length",
                f"{run_id},{video_id},0,0,1,1",
                f"{run_id},{video_id},0,0,2,1",
                f"{run_id},{video_id},1,100,2,2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return run_id


def _make_video(path: Path, frame_count: int) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for index in range(frame_count):
        writer.write(np.full((48, 64, 3), index, dtype=np.uint8))
    writer.release()
    return path
