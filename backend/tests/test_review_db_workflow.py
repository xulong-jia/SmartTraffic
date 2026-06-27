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
    RuleExecutionRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    VideoRepository,
)
from app.services.event_lifecycle_service import EventLifecycleService
from app.services.event_rule_service import EventRuleDbService
from app.services.zone_service import ZoneDbService


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


def test_rule_rerun_executes_event_rules_only_from_db_trajectory(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_rule_rerun_fixture(session)
        session.commit()

    response = client.post(
        "/api/review/events/event-rerun-source/rerun-rule",
        json={
            "run_id": "run-rerun-db",
            "comment": "rerun flow rule",
            "reviewer": "operator_5",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["rerun_scope"] == "event_rules_only"
    assert payload["result"]["rerun_scope"] == "event_rules_only"
    assert payload["result"]["trajectory_frame_count"] == 2
    assert payload["result"]["rule_count"] == 1
    assert payload["result"]["generated_event_count"] == 1
    assert payload["result"]["generated_rule_execution_count"] >= 1

    with session_factory() as session:
        task = ProcessingTaskRepository(session).get(payload["task_id"])
        assert task.status == "completed"
        assert task.result["rerun_scope"] == "event_rules_only"
        rerun_events = [
            event
            for event in EventRepository(session).list(run_id="run-rerun-db")
            if event.id.startswith("rerun_")
        ]
        assert len(rerun_events) == 1
        assert rerun_events[0].type == "flow_counting"
        assert rerun_events[0].payload["rerun_source_event_id"] == "event-rerun-source"
        executions = RuleExecutionRepository(session).list(run_id="run-rerun-db")
        matched_rerun_executions = [
            execution
            for execution in executions
            if execution.details.get("rerun_task_id") == payload["task_id"]
            and execution.status == "matched"
        ]
        assert matched_rerun_executions
        assert matched_rerun_executions[0].details["rerun_scope"] == "event_rules_only"


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


def _seed_rule_rerun_fixture(session: Session) -> None:
    VideoRepository(session).create(
        id="video-rerun-db",
        filename="rerun.mp4",
        storage_path="local_videos/rerun.mp4",
        status="completed",
    )
    zone = ZoneDbService(session).create_zone(
        {
            "id": "zone-rerun-counting",
            "name": "Rerun counting zone",
            "zone_type": "counting_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "counting_line": {
                "start_point": [50, 0],
                "end_point": [50, 100],
                "in_direction": "positive",
                "enabled": True,
            },
            "video_id": "video-rerun-db",
        }
    )
    rule = EventRuleDbService(session).create_rule(
        {
            "id": "rule-rerun-flow",
            "name": "Rerun flow count",
            "event_type": "flow_counting",
            "zone_id": zone["id"],
            "target_classes": ["car"],
            "parameters": {},
            "severity": "low",
            "min_track_length": 1,
        }
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-rerun-db",
        video_id="video-rerun-db",
        status="completed",
        result_dir="results/traffic_analysis/run-rerun-db",
        artifact_index={},
        summary={
            "event_config_snapshot": {
                "zones": [zone],
                "event_rules": [rule],
            }
        },
    )
    EventLifecycleService(session).create_event_with_evidence(
        run_id="run-rerun-db",
        video_id="video-rerun-db",
        event_id="event-rerun-source",
        event_type="flow_counting",
        status="pending",
        severity="low",
        track_id="44",
        frame_index=2,
        rule_id=rule["id"],
        zone_id=zone["id"],
        payload={},
    )
    repo = TrajectoryPointRepository(session)
    repo.create(
        id="tp-rerun-1",
        run_id="run-rerun-db",
        video_id="video-rerun-db",
        track_id="44",
        frame_index=1,
        timestamp_ms=100.0,
        x=40.0,
        y=50.0,
        speed=12.0,
        direction=None,
        features={
            "track_id": 44,
            "class_name": "car",
            "track_length": 1,
            "center": [40.0, 50.0],
            "bottom_center": [40.0, 50.0],
        },
    )
    repo.create(
        id="tp-rerun-2",
        run_id="run-rerun-db",
        video_id="video-rerun-db",
        track_id="44",
        frame_index=2,
        timestamp_ms=200.0,
        x=60.0,
        y=50.0,
        speed=12.0,
        direction=None,
        features={
            "track_id": 44,
            "class_name": "car",
            "track_length": 2,
            "center": [60.0, 50.0],
            "bottom_center": [60.0, 50.0],
            "line_crossings": [
                {
                    "line_id": zone["id"],
                    "direction": "positive",
                    "previous_point": [40.0, 50.0],
                    "current_point": [60.0, 50.0],
                }
            ],
        },
    )
