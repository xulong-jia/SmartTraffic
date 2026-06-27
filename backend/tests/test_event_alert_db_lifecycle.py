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
    AlertRepository,
    EventRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    VideoRepository,
)
from app.services.event_lifecycle_service import EventLifecycleService


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage3cd-events.db'}",
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


def test_event_evidence_rule_execution_and_analysis_runs_db_first(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_run(session)
        service = EventLifecycleService(session)
        event = service.create_event_with_evidence(
            run_id="run-3cd",
            video_id="video-3cd",
            event_id="event-3cd-1",
            event_type="danger_zone_intrusion",
            status="pending",
            severity="high",
            track_id="9",
            frame_index=12,
            rule_id="rule-3cd",
            zone_id="zone-3cd",
            payload={"class_name": "car"},
            evidence=[
                {
                    "id": "evidence-3cd-1",
                    "evidence_type": "zone_intrusion",
                    "payload": {"zone_id": "zone-3cd"},
                }
            ],
        )
        service.create_rule_execution(
            run_id="run-3cd",
            rule_id="rule-3cd",
            event_id=event["id"],
            status="matched",
            matched_count=1,
            details={"event_id": event["id"]},
        )
        session.commit()

    list_response = client.get(
        "/api/events?run_id=run-3cd&event_type=danger_zone_intrusion"
        "&status=pending&severity=high&track_id=9"
    )
    assert list_response.status_code == 200
    assert list_response.json()["source"] == "db"
    assert list_response.json()["items"][0]["id"] == "event-3cd-1"

    detail_response = client.get("/api/events/event-3cd-1")
    assert detail_response.status_code == 200
    assert detail_response.json()["event_evidence"][0]["id"] == "evidence-3cd-1"

    analysis_response = client.get("/api/analysis-runs/run-3cd/events")
    assert analysis_response.status_code == 200
    analysis_payload = analysis_response.json()
    assert analysis_payload["source"] == "db"
    assert analysis_payload["events"][0]["event_id"] == "event-3cd-1"
    assert analysis_payload["event_evidence"][0]["id"] == "evidence-3cd-1"
    assert analysis_payload["rule_executions"][0]["rule_id"] == "rule-3cd"
    rule_response = client.get("/api/analysis-runs/run-3cd/events?rule_id=rule-3cd")
    assert rule_response.status_code == 200
    assert rule_response.json()["rule_executions"][0]["rule_id"] == "rule-3cd"

    review_response = client.get(
        "/api/review/events/event-3cd-1?run_id=run-3cd"
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["event_evidence"][0]["id"] == "evidence-3cd-1"
    assert review_payload["rule_executions"][0]["rule_id"] == "rule-3cd"

    patch_response = client.patch(
        "/api/events/event-3cd-1/status",
        json={"status": "confirmed"},
    )
    assert patch_response.status_code == 200
    with session_factory() as session:
        assert EventRepository(session).get("event-3cd-1").status == "confirmed"


def test_alert_api_is_db_backed_and_status_transitions_persist(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_run(session)
        event = EventLifecycleService(session).create_event_with_evidence(
            run_id="run-3cd",
            video_id="video-3cd",
            event_id="event-alert-1",
            event_type="wrong_way_driving",
            status="pending",
            severity="high",
            track_id="11",
            frame_index=22,
            payload={},
        )
        alert = EventLifecycleService(session).create_alert_for_event(event["id"])
        session.commit()

    list_response = client.get("/api/alerts?run_id=run-3cd&status=new&level=critical")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    alert_id = list_response.json()["alerts"][0]["id"]
    assert alert_id == alert["id"]

    ack_response = client.patch(
        f"/api/alerts/{alert_id}/acknowledge",
        json={"acknowledged_by": "operator_db"},
    )
    assert ack_response.status_code == 200
    acknowledged = ack_response.json()
    assert acknowledged["status"] == "acknowledged"
    assert acknowledged["acknowledged_by"] == "operator_db"
    assert acknowledged["acknowledged_at"]

    resolve_response = client.patch(f"/api/alerts/{alert_id}/resolve")
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"
    assert resolve_response.json()["resolved_at"]

    ignore_response = client.patch(f"/api/alerts/{alert_id}/ignore")
    assert ignore_response.status_code == 200
    assert ignore_response.json()["status"] == "ignored"

    with session_factory() as session:
        stored = AlertRepository(session).get(alert_id)
        assert stored.status == "ignored"
        assert stored.payload["acknowledged_by"] == "operator_db"
        assert stored.payload["resolved_at"]


def test_alert_api_not_found_returns_404(client: TestClient) -> None:
    assert client.get("/api/alerts/missing-alert").status_code == 404
    assert client.patch("/api/alerts/missing-alert/acknowledge").status_code == 404
    assert client.patch("/api/alerts/missing-alert/resolve").status_code == 404
    assert client.patch("/api/alerts/missing-alert/ignore").status_code == 404


def test_standalone_track_and_trajectory_apis_read_db_results(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_run(session)
        TrackRepository(session).create(
            id="track-row-3cd",
            run_id="run-3cd",
            video_id="video-3cd",
            track_id="9",
            class_name="car",
            start_frame=12,
            end_frame=16,
            confidence=0.93,
            metadata_json={"state": "confirmed"},
        )
        TrajectoryPointRepository(session).create(
            id="trajectory-row-3cd",
            run_id="run-3cd",
            video_id="video-3cd",
            track_id="9",
            frame_index=12,
            timestamp_ms=480,
            x=120.5,
            y=80.25,
            speed=4.5,
            direction="90",
            features={"source": "test"},
        )
        session.commit()

    tracks_response = client.get("/api/tracks?run_id=run-3cd&track_id=9")
    assert tracks_response.status_code == 200
    tracks_payload = tracks_response.json()
    assert tracks_payload["source"] == "db"
    assert tracks_payload["summary"]["total_tracks"] == 1
    assert tracks_payload["rows"][0]["track_id"] == "9"

    trajectories_response = client.get(
        "/api/trajectories?run_id=run-3cd&track_id=9"
    )
    assert trajectories_response.status_code == 200
    trajectories_payload = trajectories_response.json()
    assert trajectories_payload["source"] == "db"
    assert trajectories_payload["summary"]["total_trajectory_points"] == 1
    assert trajectories_payload["rows"][0]["x"] == 120.5


def _seed_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-3cd",
        filename="stage3cd.mp4",
        storage_path="local_videos/stage3cd.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-3cd",
        video_id="video-3cd",
        status="completed",
        result_dir="results/traffic_analysis/run-3cd",
        artifact_index={},
    )
