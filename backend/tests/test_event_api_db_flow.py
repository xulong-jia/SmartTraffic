from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from app.repositories import (
    EventEvidenceRepository,
    EventRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage3ab.db'}",
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

    def override_get_db():
        with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


def test_top_level_event_api_db_first_status_update_and_bad_case(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_run(session)
        EventRepository(session).create(
            id="event-db-1",
            run_id="run-db-1",
            video_id="video-db-1",
            type="danger_zone_intrusion",
            status="pending",
            severity="high",
            frame_index=12,
            track_id="42",
            payload={"event_id": "event-db-1", "class_name": "car"},
        )
        EventEvidenceRepository(session).create(
            id="evidence-db-1",
            event_id="event-db-1",
            run_id="run-db-1",
            evidence_type="zone_intrusion",
            payload={"zone_id": "zone-db-1"},
        )
        session.commit()

    list_response = client.get(
        "/api/events?run_id=run-db-1&event_type=danger_zone_intrusion&status=pending"
        "&severity=high&track_id=42"
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["source"] == "db"
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == "event-db-1"

    detail_response = client.get("/api/events/event-db-1")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == "event-db-1"
    assert detail_payload["event_evidence"][0]["id"] == "evidence-db-1"

    patch_response = client.patch(
        "/api/events/event-db-1/status",
        json={"status": "confirmed"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "confirmed"

    bad_case_response = client.post(
        "/api/events/event-db-1/bad-case",
        json={
            "case_type": "false_positive",
            "module": "event_engine",
            "description": "event should be reviewed",
            "expected_result": "no event",
            "actual_result": "event emitted",
            "tags": ["stage3ab"],
        },
    )
    assert bad_case_response.status_code == 201
    bad_case = bad_case_response.json()
    assert bad_case["event_id"] == "event-db-1"
    assert bad_case["run_id"] == "run-db-1"
    assert bad_case["video_id"] == "video-db-1"
    assert bad_case["track_id"] == "42"
    assert bad_case["case_type"] == "false_positive"


def test_top_level_event_api_not_found_returns_404(client: TestClient) -> None:
    assert client.get("/api/events/missing-event").status_code == 404
    assert (
        client.patch(
            "/api/events/missing-event/status",
            json={"status": "confirmed"},
        ).status_code
        == 404
    )
    assert client.post(
        "/api/events/missing-event/bad-case",
        json={"case_type": "other", "module": "event_engine"},
    ).status_code == 404


def test_top_level_event_api_artifact_fallback(
    client: TestClient,
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(
        "run-artifact-events",
        {"video_id": "video-artifact-1", "artifacts": {}},
    )
    writer.write_event_outputs(
        run_id="run-artifact-events",
        video_id="video-artifact-1",
        events=[
            {
                "event_id": "event-artifact-1",
                "run_id": "run-artifact-events",
                "video_id": "video-artifact-1",
                "event_type": "illegal_parking",
                "status": "pending",
                "severity": "medium",
                "track_id": 9,
                "start_frame": 3,
                "evidence": {"source": "artifact"},
            }
        ],
        event_evidence=[],
        rule_executions=[],
    )

    list_response = client.get("/api/events?run_id=run-artifact-events")
    assert list_response.status_code == 200
    assert list_response.json()["source"] == "artifact"
    assert list_response.json()["items"][0]["id"] == "event-artifact-1"

    detail_response = client.get(
        "/api/events/event-artifact-1?run_id=run-artifact-events"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["source"] == "artifact"


def _seed_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-db-1",
        filename="events.mp4",
        storage_path="local_videos/events.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-db-1",
        video_id="video-db-1",
        status="completed",
        result_dir="results/traffic_analysis/run-db-1",
        artifact_index={},
    )
