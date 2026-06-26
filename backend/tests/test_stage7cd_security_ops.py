from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from app.repositories import (
    EventRepository,
    ProcessingTaskRepository,
    ReviewCommentRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)
from app.services.event_lifecycle_service import EventLifecycleService


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage7cd-security.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


def test_strict_mode_viewer_cannot_mutate_zone_but_permissive_allows(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "id": "zone-security-1",
        "name": "Security Zone",
        "zone_type": "danger_zone",
        "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "enabled": True,
    }
    monkeypatch.setenv("SMARTTRAFFIC_AUTH_MODE", "strict")
    denied = client.post(
        "/api/zones",
        json=payload,
        headers={"X-SmartTraffic-Actor": "viewer_1", "X-SmartTraffic-Role": "viewer"},
    )
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "permission_denied"

    monkeypatch.setenv("SMARTTRAFFIC_AUTH_MODE", "permissive")
    allowed = client.post(
        "/api/zones",
        json=payload,
        headers={"X-SmartTraffic-Actor": "viewer_1", "X-SmartTraffic-Role": "viewer"},
    )
    assert allowed.status_code == 201


def test_actor_header_drives_alert_acknowledge_review_and_rerun_audit(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_AUTH_MODE", "strict")
    with session_factory() as session:
        _seed_run(session)
        event = EventLifecycleService(session).create_event_with_evidence(
            run_id="run-security",
            video_id="video-security",
            event_id="event-security-1",
            event_type="wrong_way_driving",
            status="pending",
            severity="high",
            frame_index=7,
            payload={},
        )
        alert = EventLifecycleService(session).create_alert_for_event(event["id"])
        session.commit()

    reviewer_headers = {
        "X-SmartTraffic-Actor": "reviewer_7",
        "X-SmartTraffic-Role": "reviewer",
    }
    operator_headers = {
        "X-SmartTraffic-Actor": "operator_7",
        "X-SmartTraffic-Role": "operator",
    }
    ack = client.patch(
        f"/api/alerts/{alert['id']}/acknowledge",
        headers=operator_headers,
    )
    assert ack.status_code == 200
    assert ack.json()["acknowledged_by"] == "operator_7"

    review = client.post(
        "/api/review/events/event-security-1/confirm",
        json={"run_id": "run-security", "comment": "confirmed by actor"},
        headers=reviewer_headers,
    )
    assert review.status_code == 200
    assert review.json()["review"]["reviewer"] == "reviewer_7"

    rerun = client.post(
        "/api/review/events/event-security-1/rerun-rule",
        json={"run_id": "run-security", "comment": "rerun by actor"},
        headers=reviewer_headers,
    )
    assert rerun.status_code == 200

    with session_factory() as session:
        comment = ReviewCommentRepository(session).list(event_id="event-security-1")[0]
        assert comment.author == "reviewer_7"
        task = ProcessingTaskRepository(session).list(mode="rule_rerun")[0]
        assert task.parameters["requested_by"] == "reviewer_7"


def test_strict_operator_can_start_realtime_and_actor_is_in_task_params(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_AUTH_MODE", "strict")
    operator_headers = {
        "X-SmartTraffic-Actor": "operator_rt",
        "X-SmartTraffic-Role": "operator",
    }
    camera_response = client.post(
        "/api/cameras",
        json={"name": "Security Mock Camera", "source_type": "mock"},
        headers=operator_headers,
    )
    assert camera_response.status_code == 201
    camera_id = camera_response.json()["id"]

    start = client.post(f"/api/realtime/{camera_id}/start", headers=operator_headers)
    assert start.status_code == 200
    video_id = start.json()["video_id"]

    status_response = client.get(f"/api/videos/{video_id}/status")
    assert status_response.status_code == 200
    params = status_response.json()["latest_task"]["params_json"]
    assert params["task_type"] == "realtime_process"
    assert params["actor"] == "operator_rt"
    assert params["role"] == "operator"


def test_bad_case_actor_tag_readiness_and_standard_error_shape(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_AUTH_MODE", "strict")
    with session_factory() as session:
        _seed_run(session)
        EventRepository(session).create(
            id="event-badcase-security",
            run_id="run-security",
            video_id="video-security",
            type="danger_zone_intrusion",
            status="pending",
            severity="medium",
            payload={},
        )
        session.commit()

    headers = {
        "X-SmartTraffic-Actor": "reviewer_badcase",
        "X-SmartTraffic-Role": "reviewer",
    }
    created = client.post(
        "/api/bad-cases",
        json={
            "run_id": "run-security",
            "event_id": "event-badcase-security",
            "case_type": "false_positive",
            "module": "event_engine",
            "description": "actor audit",
            "tags": ["security"],
        },
        headers=headers,
    )
    assert created.status_code == 200
    assert "actor:reviewer_badcase" in created.json()["tags"]

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"

    missing = client.get("/api/cameras/missing-camera")
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "not_found"
    assert "Traceback" not in str(missing.json())


def _seed_run(session: Session) -> None:
    if VideoRepository(session).get("video-security") is None:
        VideoRepository(session).create(
            id="video-security",
            filename="security.mp4",
            storage_path="local_videos/security.mp4",
            status="completed",
        )
    if TrafficAnalysisRunRepository(session).get("run-security") is None:
        TrafficAnalysisRunRepository(session).create(
            id="run-security",
            video_id="video-security",
            status="completed",
            result_dir="results/traffic_analysis/run-security",
            artifact_index={},
        )
