from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.event_rule_service import event_rule_service


@pytest.fixture(autouse=True)
def clear_event_rules():
    event_rule_service.clear()
    yield
    event_rule_service.clear()


def test_event_rule_api_create_get_update_delete() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/event-rules",
        json={
            "id": "rule_wrong_way_1",
            "name": "Wrong Way",
            "event_type": "wrong_way_driving",
            "enabled": True,
            "zone_id": "zone_lane_1",
            "target_classes": ["car", "truck"],
            "parameters": {"min_speed_px_per_frame": 1.0},
            "cooldown_seconds": 5,
            "severity": "high",
            "version": 2,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == "rule_wrong_way_1"
    assert created["event_type"] == "wrong_way_driving"
    assert created["target_classes"] == ["car", "truck"]
    assert created["version"] == 2

    list_response = client.get("/api/event-rules?event_type=wrong_way_driving&enabled=true")
    assert list_response.status_code == 200
    assert [rule["id"] for rule in list_response.json()] == ["rule_wrong_way_1"]

    get_response = client.get("/api/event-rules/rule_wrong_way_1")
    assert get_response.status_code == 200
    assert get_response.json()["zone_id"] == "zone_lane_1"

    update_response = client.patch(
        "/api/event-rules/rule_wrong_way_1",
        json={"enabled": False, "cooldown_seconds": 10},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False
    assert update_response.json()["cooldown_seconds"] == 10.0

    delete_response = client.delete("/api/event-rules/rule_wrong_way_1")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"id": "rule_wrong_way_1", "deleted": True}
    assert client.get("/api/event-rules/rule_wrong_way_1").status_code == 404


def test_event_rule_api_filters_by_zone_id() -> None:
    client = TestClient(app)
    client.post(
        "/api/event-rules",
        json={
            "id": "rule_zone_a",
            "name": "Danger A",
            "event_type": "danger_zone_intrusion",
            "zone_id": "zone_a",
        },
    )
    client.post(
        "/api/event-rules",
        json={
            "id": "rule_zone_b",
            "name": "Danger B",
            "event_type": "danger_zone_intrusion",
            "zone_id": "zone_b",
        },
    )

    response = client.get("/api/event-rules?zone_id=zone_b")

    assert response.status_code == 200
    assert [rule["id"] for rule in response.json()] == ["rule_zone_b"]


def test_event_rule_api_rejects_unsupported_event_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/event-rules",
        json={
            "id": "rule_unknown",
            "name": "Unknown",
            "event_type": "unknown_event",
        },
    )

    assert response.status_code == 422
