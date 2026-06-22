from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_stage_three_tracking_api_upload_process_and_query(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()

    video_path = tmp_path / "upload.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for _ in range(4):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    client = TestClient(app)
    with video_path.open("rb") as file:
        upload_response = client.post(
            "/api/videos/upload",
            files={"file": ("upload.mp4", file, "video/mp4")},
        )

    assert upload_response.status_code == 200
    video_id = upload_response.json()["id"]

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking",
            "detector_dry_run": True,
            "tracker_dry_run": True,
            "frame_stride": 2,
            "max_frames": 2,
        },
    )

    assert process_response.status_code == 200
    process_payload = process_response.json()
    assert process_payload["status"] == "completed"
    assert process_payload["stage"] == "stage_3_deepsort_tracking"
    assert process_payload["next_stage"] == "stage_4_trajectory_engine_not_started"
    assert process_payload["total_frames_processed"] == 2
    assert process_payload["total_tracks"] == 0
    run_id = process_payload["run_id"]

    run_response = client.get(f"/api/analysis-runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["id"] == run_id

    tracks_response = client.get(f"/api/analysis-runs/{run_id}/tracks?limit=10")
    assert tracks_response.status_code == 200
    tracks_payload = tracks_response.json()
    assert tracks_payload["run_id"] == run_id
    assert tracks_payload["summary"]["total_frames_processed"] == 2
    assert len(tracks_payload["frames"]) == 2
