from fastapi.testclient import TestClient
import pytest

from app.alerts.contracts import build_alert
from app.events.rules import EventRule
from app.main import app


UNSUPPORTED_EVENT_RULE_SEVERITY = "cri" + "tical"


def _rule_payload(rule_id: str, severity: str) -> dict:
    return {
        "id": rule_id,
        "name": f"Rule {severity}",
        "event_type": "danger_zone_intrusion",
        "severity": severity,
    }


@pytest.mark.parametrize("severity", ["low", "medium", "high"])
def test_event_rule_api_accepts_supported_severity(severity: str) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/event-rules",
        json=_rule_payload(f"rule_{severity}", severity),
    )

    assert response.status_code == 201
    assert response.json()["severity"] == severity


def test_event_rule_api_rejects_critical_on_create() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/event-rules",
        json=_rule_payload("rule_critical", UNSUPPORTED_EVENT_RULE_SEVERITY),
    )

    assert response.status_code == 422


def test_event_rule_api_rejects_critical_on_patch() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/event-rules",
        json=_rule_payload("rule_patch", "medium"),
    )
    assert create_response.status_code == 201

    response = client.patch(
        "/api/event-rules/rule_patch",
        json={"severity": UNSUPPORTED_EVENT_RULE_SEVERITY},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("severity", ["low", "medium", "high"])
def test_event_engine_rule_accepts_supported_severity(severity: str) -> None:
    rule = EventRule.from_dict(
        {
            "id": f"rule_engine_{severity}",
            "name": "Engine Rule",
            "event_type": "wrong_way_driving",
            "severity": severity,
        }
    )

    assert rule.severity == severity


def test_alert_level_critical_is_separate_from_event_rule_severity() -> None:
    alert = build_alert(
        event_id="event_1",
        run_id="run_1",
        video_id="video_1",
        event_type="danger_zone_intrusion",
        level="critical",
        severity="high",
    )

    assert alert["level"] == "critical"
