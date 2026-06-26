from fastapi.testclient import TestClient

from app.main import app


def test_camera_api_crud_masks_stream_url() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/cameras",
        json={
            "name": "North Gate RTSP",
            "location": "north-gate",
            "source_type": "rtsp",
            "stream_url": "rtsp://user:secret@example.local:554/live/main",
            "width": 1280,
            "height": 720,
            "fps": 25.0,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    camera_id = created["id"]
    assert created["source_type"] == "rtsp"
    assert created["masked_stream_url"] == "rtsp://***@example.local:554/..."
    assert "stream_url" not in created
    assert "secret" not in str(created)

    list_response = client.get("/api/cameras")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert [camera["id"] for camera in listed] == [camera_id]
    assert "stream_url" not in listed[0]
    assert "secret" not in str(listed)

    detail_response = client.get(f"/api/cameras/{camera_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["masked_stream_url"] == created["masked_stream_url"]

    update_response = client.patch(
        f"/api/cameras/{camera_id}",
        json={"name": "Updated North Gate", "source_type": "mock"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated North Gate"
    assert update_response.json()["source_type"] == "mock"

    disable_response = client.post(f"/api/cameras/{camera_id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False
    assert disable_response.json()["status"] == "disabled"

    enable_response = client.post(f"/api/cameras/{camera_id}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True
    assert enable_response.json()["status"] == "active"

    filtered_response = client.get("/api/cameras?enabled=true&source_type=mock")
    assert filtered_response.status_code == 200
    assert [camera["id"] for camera in filtered_response.json()] == [camera_id]

    delete_response = client.delete(f"/api/cameras/{camera_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "camera_id": camera_id}
    assert client.get(f"/api/cameras/{camera_id}").status_code == 404


def test_camera_api_rejects_invalid_source_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/cameras",
        json={
            "name": "Unsupported Camera",
            "source_type": "websocket",
            "stream_url": "mock://source",
        },
    )

    assert response.status_code == 400
    assert "source_type must be one of" in response.json()["detail"]


def test_camera_api_not_found() -> None:
    client = TestClient(app)

    assert client.get("/api/cameras/missing-camera").status_code == 404
    assert client.patch("/api/cameras/missing-camera", json={"name": "x"}).status_code == 404
    assert client.delete("/api/cameras/missing-camera").status_code == 404
