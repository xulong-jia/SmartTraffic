from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_mock_realtime_preview_lifecycle_creates_processing_task() -> None:
    client = TestClient(app)
    camera_id = _create_camera(client, source_type="mock")["id"]

    start_response = client.post(f"/api/realtime/{camera_id}/start")

    assert start_response.status_code == 200
    started = start_response.json()
    assert started["status"] == "running"
    assert started["task_type"] == "realtime_process"
    assert started["task_id"].startswith("rt_task_")
    assert started["video_id"].startswith("rt_video_")
    assert started["frame_count"] == 3
    assert "secret" not in str(started)

    video_status_response = client.get(f"/api/videos/{started['video_id']}/status")
    assert video_status_response.status_code == 200
    latest_task = video_status_response.json()["latest_task"]
    assert latest_task["status"] == "running"
    assert latest_task["params_json"]["task_type"] == "realtime_process"
    assert latest_task["params_json"]["camera_id"] == camera_id

    status_response = client.get(f"/api/realtime/{camera_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "running"

    frames_response = client.get(f"/api/realtime/{camera_id}/recent-frames")
    assert frames_response.status_code == 200
    frames = frames_response.json()
    assert frames["total"] == 3
    assert frames["max_items"] == 20
    assert {frame["status"] for frame in frames["items"]} == {"mock_frame"}

    events_response = client.get(f"/api/realtime/{camera_id}/recent-events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert events["total"] == 1
    assert events["items"][0]["event_type"] == "realtime_preview_motion"
    assert events["items"][0]["evidence"]["type"] == "preview_frame_metadata"

    alerts_response = client.get(f"/api/realtime/{camera_id}/recent-alerts")
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["event_type"] == "realtime_preview_motion"

    stop_response = client.post(f"/api/realtime/{camera_id}/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"

    stopped_video_status = client.get(f"/api/videos/{started['video_id']}/status").json()
    assert stopped_video_status["latest_task"]["status"] == "completed"
    assert stopped_video_status["latest_task"]["progress"] == 1.0


def test_disabled_camera_cannot_start_realtime_preview() -> None:
    client = TestClient(app)
    camera_id = _create_camera(client, source_type="mock", enabled=False)["id"]

    response = client.post(f"/api/realtime/{camera_id}/start")

    assert response.status_code == 400
    assert response.json()["detail"] == "disabled camera cannot start realtime preview"


def test_file_realtime_preview_uses_safe_source_label(tmp_path: Path) -> None:
    client = TestClient(app)
    source_file = tmp_path / "preview.mp4"
    source_file.write_bytes(b"placeholder-video")
    camera_id = _create_camera(
        client,
        source_type="file",
        stream_url=str(source_file),
    )["id"]

    start_response = client.post(f"/api/realtime/{camera_id}/start")

    assert start_response.status_code == 200
    frames_response = client.get(f"/api/realtime/{camera_id}/recent-frames")
    frame = frames_response.json()["items"][0]
    assert frame["source_type"] == "file"
    assert frame["source_label"] == "preview.mp4"
    assert frame["status"] == "file_preview_available"
    assert str(tmp_path) not in str(frames_response.json())


def test_rtsp_realtime_preview_has_no_real_rtsp_dependency() -> None:
    client = TestClient(app)
    camera_id = _create_camera(
        client,
        source_type="rtsp",
        stream_url="rtsp://user:secret@example.local/live",
    )["id"]

    start_response = client.post(f"/api/realtime/{camera_id}/start")

    assert start_response.status_code == 200
    frames_response = client.get(f"/api/realtime/{camera_id}/recent-frames")
    frame = frames_response.json()["items"][0]
    assert frame["status"] == "rtsp_preview_not_connected"
    assert frame["source_label"] == "rtsp://***@example.local/..."
    assert "secret" not in str(start_response.json())
    assert "secret" not in str(frames_response.json())


def test_realtime_preview_not_found() -> None:
    client = TestClient(app)

    assert client.post("/api/realtime/missing-camera/start").status_code == 404
    assert client.post("/api/realtime/missing-camera/stop").status_code == 404
    assert client.get("/api/realtime/missing-camera/status").status_code == 404
    assert client.get("/api/realtime/missing-camera/recent-frames").status_code == 404
    assert client.get("/api/realtime/missing-camera/recent-events").status_code == 404
    assert client.get("/api/realtime/missing-camera/recent-alerts").status_code == 404


def _create_camera(
    client: TestClient,
    *,
    source_type: str,
    stream_url: str | None = None,
    enabled: bool = True,
) -> dict:
    response = client.post(
        "/api/cameras",
        json={
            "name": f"{source_type} camera",
            "source_type": source_type,
            "stream_url": stream_url,
            "enabled": enabled,
            "width": 640,
            "height": 360,
            "fps": 10.0,
        },
    )
    assert response.status_code == 201
    return response.json()
