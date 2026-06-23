from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.zone_service import zone_service


@pytest.fixture(autouse=True)
def clear_zones():
    zone_service.clear()
    yield
    zone_service.clear()


def test_zone_api_create_get_update_delete() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/zones",
        json={
            "id": "zone_lane_1",
            "name": "Vehicle Lane",
            "zone_type": "vehicle_lane",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "direction": {
                "start_point": [0, 50],
                "end_point": [100, 50],
                "allowed_angle": 0,
                "reverse_angle_threshold": 135,
            },
            "counting_line": {
                "start_point": [50, 0],
                "end_point": [50, 100],
                "in_direction": "positive",
                "enabled": True,
            },
            "enabled": True,
            "video_id": "video_001",
            "camera_id": "camera_001",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == "zone_lane_1"
    assert created["zone_type"] == "vehicle_lane"
    assert created["direction"]["allowed_angle"] == 0.0
    assert created["counting_line"]["in_direction"] == "positive"

    list_response = client.get("/api/zones?video_id=video_001")
    assert list_response.status_code == 200
    assert [zone["id"] for zone in list_response.json()] == ["zone_lane_1"]

    get_response = client.get("/api/zones/zone_lane_1")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Vehicle Lane"

    update_response = client.patch(
        "/api/zones/zone_lane_1",
        json={"name": "Updated Lane", "enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Lane"
    assert update_response.json()["enabled"] is False

    delete_response = client.delete("/api/zones/zone_lane_1")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"id": "zone_lane_1", "deleted": True}
    assert client.get("/api/zones/zone_lane_1").status_code == 404


def test_zone_api_filters_enabled() -> None:
    client = TestClient(app)
    client.post(
        "/api/zones",
        json={
            "id": "zone_enabled",
            "name": "Enabled Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "enabled": True,
        },
    )
    client.post(
        "/api/zones",
        json={
            "id": "zone_disabled",
            "name": "Disabled Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "enabled": False,
        },
    )

    response = client.get("/api/zones?enabled=true")

    assert response.status_code == 200
    assert [zone["id"] for zone in response.json()] == ["zone_enabled"]
