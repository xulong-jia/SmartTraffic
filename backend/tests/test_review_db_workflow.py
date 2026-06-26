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
        f"sqlite:///{tmp_path / 'stage3cd-review.db'}",
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


def test_review_db_actions_write_audit_trail(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_review_event(session)
        session.commit()

    list_response = client.get("/api/review/events?run_id=run-review-db")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["review_status"] == "pending"

    confirm = client.post(
        "/api/review/events/event-review-1/confirm",
        json={
            "run_id": "run-review-db",
            "comment": "confirmed",
            "reviewer": "operator_1",
        },
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    assert confirm.json()["review"]["before_status"] == "pending"
    assert confirm.json()["review"]["after_status"] == "confirmed"

    comment = client.post(
        "/api/review/comments",
        json={
            "run_id": "run-review-db",
            "event_id": "event-review-1",
            "comment": "second note",
            "reviewer": "operator_2",
        },
    )
    assert comment.status_code == 200
    assert comment.json()["status"] == "confirmed"

    with session_factory() as session:
        event = EventRepository(session).get("event-review-1")
        assert event.status == "confirmed"
        comments = ReviewCommentRepository(session).list(event_id="event-review-1")
        assert [item.payload["action"] for item in comments] == ["confirm", "comment"]
        assert comments[0].payload["before_status"] == "pending"
        assert comments[0].payload["after_status"] == "confirmed"
        assert comments[1].author == "operator_2"


def test_review_false_positive_ignore_resolve_false_negative_and_rerun_request(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_review_event(session, event_id="event-review-2")
        session.commit()

    false_positive = client.post(
        "/api/review/events/event-review-2/false-positive",
        json={"run_id": "run-review-db", "comment": "wrong match"},
    )
    assert false_positive.status_code == 200
    assert false_positive.json()["status"] == "false_positive"

    resolved = client.post(
        "/api/review/events/event-review-2/resolve",
        json={"run_id": "run-review-db"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    ignored = client.post(
        "/api/review/events/event-review-2/ignore",
        json={"run_id": "run-review-db"},
    )
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "ignored"

    false_negative = client.post(
        "/api/review/events/false-negative",
        json={
            "run_id": "run-review-db",
            "expected_event_type": "illegal_parking",
            "description": "missed db event",
            "reviewer": "operator_3",
        },
    )
    assert false_negative.status_code == 200
    assert false_negative.json()["status"] == "false_negative"
    assert false_negative.json()["event_id"].startswith("fn_")

    rerun = client.post(
        "/api/review/events/event-review-2/rerun-rule",
        json={
            "run_id": "run-review-db",
            "comment": "rerun requested",
            "reviewer": "operator_4",
        },
    )
    assert rerun.status_code == 200
    assert rerun.json()["status"] == "pending"

    with session_factory() as session:
        task = ProcessingTaskRepository(session).list(mode="rule_rerun")[0]
        assert task.status == "pending"
        assert task.parameters["event_id"] == "event-review-2"
        assert task.parameters["run_id"] == "run-review-db"
        assert task.parameters["requested_by"] == "operator_4"


def _seed_review_event(session: Session, *, event_id: str = "event-review-1") -> None:
    if VideoRepository(session).get("video-review-db") is None:
        VideoRepository(session).create(
            id="video-review-db",
            filename="review.mp4",
            storage_path="local_videos/review.mp4",
            status="completed",
        )
    if TrafficAnalysisRunRepository(session).get("run-review-db") is None:
        TrafficAnalysisRunRepository(session).create(
            id="run-review-db",
            video_id="video-review-db",
            status="completed",
            result_dir="results/traffic_analysis/run-review-db",
            artifact_index={},
        )
    EventLifecycleService(session).create_event_with_evidence(
        run_id="run-review-db",
        video_id="video-review-db",
        event_id=event_id,
        event_type="danger_zone_intrusion",
        status="pending",
        severity="high",
        track_id="31",
        frame_index=5,
        rule_id="rule-review-db",
        payload={},
    )
