from fastapi.testclient import TestClient

from app.main import app


def test_zone_db_crud_exposes_version_and_filters() -> None:
    client = TestClient(app)
    payload = {
        "id": "zone-db-1",
        "name": "Main lane",
        "zone_type": "vehicle_lane",
        "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "direction": {"allowed_angle": 90, "reverse_angle_threshold": 160},
        "counting_line": {
            "start_point": [0, 5],
            "end_point": [10, 5],
            "in_direction": "positive",
        },
        "enabled": True,
        "video_id": "video-db-1",
        "camera_id": "camera-db-1",
        "version": 2,
    }

    create_response = client.post("/api/zones", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == "zone-db-1"
    assert created["version"] == 2
    assert created["counting_line"]["in_direction"] == "positive"

    list_response = client.get("/api/zones?video_id=video-db-1&enabled=true")
    assert list_response.status_code == 200
    assert [zone["id"] for zone in list_response.json()] == ["zone-db-1"]

    patch_response = client.patch(
        "/api/zones/zone-db-1",
        json={"enabled": False, "version": 3},
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["enabled"] is False
    assert updated["version"] == 3

    assert client.get("/api/zones?enabled=true").json() == []
    delete_response = client.delete("/api/zones/zone-db-1")
    assert delete_response.status_code == 200
    assert client.get("/api/zones/zone-db-1").status_code == 404


def test_event_rule_db_crud_exposes_version_and_filters() -> None:
    client = TestClient(app)
    zone_response = client.post(
        "/api/zones",
        json={
            "id": "zone-rule-1",
            "name": "Danger zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]],
        },
    )
    assert zone_response.status_code == 201

    create_response = client.post(
        "/api/event-rules",
        json={
            "id": "rule-db-1",
            "name": "Danger intrusion",
            "event_type": "danger_zone_intrusion",
            "enabled": True,
            "zone_id": "zone-rule-1",
            "target_classes": ["car", "bus"],
            "parameters": {"min_dwell_frames": 2},
            "cooldown_seconds": 5,
            "severity": "high",
            "version": 4,
            "min_track_length": 2,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == "rule-db-1"
    assert created["version"] == 4
    assert created["target_classes"] == ["car", "bus"]

    list_response = client.get(
        "/api/event-rules?event_type=danger_zone_intrusion&enabled=true&zone_id=zone-rule-1"
    )
    assert list_response.status_code == 200
    assert [rule["id"] for rule in list_response.json()] == ["rule-db-1"]

    patch_response = client.patch(
        "/api/event-rules/rule-db-1",
        json={"enabled": False, "version": 5, "severity": "medium"},
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["enabled"] is False
    assert updated["version"] == 5
    assert updated["severity"] == "medium"

    assert client.get("/api/event-rules?enabled=true").json() == []
    assert (
        client.patch("/api/event-rules/missing", json={"enabled": True}).status_code
        == 404
    )
