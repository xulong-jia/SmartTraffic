from collections.abc import Generator
import json
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
    BadCaseRepository,
    EventRepository,
    ReviewCommentRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage3ef-bad-cases.db'}",
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
    monkeypatch.setenv("SMARTTRAFFIC_EVALS_DIR", str(tmp_path / "evals"))

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


def test_bad_case_db_create_list_detail_update_summary_and_filters(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    with session_factory() as session:
        _seed_run(session, tmp_path)
        session.commit()

    created = client.post(
        "/api/bad-cases",
        json={
            "run_id": "run-bad-db",
            "video_id": "video-bad-db",
            "event_id": "event-bad-db",
            "track_id": 17,
            "frame_index": 42,
            "case_type": "zone_config_error",
            "module": "zone_config",
            "description": "zone polygon caused wrong event",
            "expected_result": "no alert",
            "actual_result": "alert raised",
            "root_cause": "polygon too wide",
            "snapshot_path": "keyframes/event-bad-db.jpg",
            "tags": ["zone", "reviewed"],
        },
    )
    assert created.status_code == 200
    case = created.json()
    assert case["case_id"].startswith("badcase_")
    assert case["case_type"] == "zone_config_error"
    assert case["module"] == "zone_config"

    listed = client.get(
        "/api/bad-cases?run_id=run-bad-db&video_id=video-bad-db"
        "&event_id=event-bad-db&case_type=zone_config_error"
        "&module=zone_config&status=open&tag=zone"
    )
    detail = client.get(f"/api/bad-cases/{case['case_id']}?run_id=run-bad-db")
    patched = client.patch(
        f"/api/bad-cases/{case['case_id']}",
        json={
            "run_id": "run-bad-db",
            "status": "ignored",
            "root_cause": "accepted configuration limitation",
            "tags": ["zone", "ignored"],
        },
    )
    summary = client.get("/api/bad-cases/summary?run_id=run-bad-db")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert detail.status_code == 200
    assert detail.json()["track_id"] == 17
    assert patched.status_code == 200
    assert patched.json()["status"] == "ignored"
    assert patched.json()["root_cause"] == "accepted configuration limitation"
    assert summary.status_code == 200
    assert summary.json()["by_type"] == {"zone_config_error": 1}
    assert summary.json()["by_status"] == {"ignored": 1}

    with session_factory() as session:
        stored = BadCaseRepository(session).get(case["case_id"])
        assert stored is not None
        assert stored.payload["video_id"] == "video-bad-db"
        assert stored.payload["frame_index"] == 42
        assert stored.payload["root_cause"] == "accepted configuration limitation"


def test_bad_case_from_review_uses_db_review_audit(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    with session_factory() as session:
        _seed_run(session, tmp_path)
        ReviewCommentRepository(session).create(
            id="review-bad-db",
            run_id="run-bad-db",
            event_id="event-bad-db",
            author="operator",
            status="false_positive",
            body="review promoted to bad case",
            payload={
                "review_id": "review-bad-db",
                "run_id": "run-bad-db",
                "event_id": "event-bad-db",
                "action": "mark_false_positive",
                "before_status": "pending",
                "after_status": "false_positive",
                "comment": "review promoted to bad case",
                "reviewer": "operator",
                "created_at": "2026-01-01T00:00:00+00:00",
                "source": "review_center",
            },
        )
        session.commit()

    response = client.post(
        "/api/bad-cases/from-review",
        json={
            "run_id": "run-bad-db",
            "review_id": "review-bad-db",
            "module": "review",
            "tags": ["review"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "review_center"
    assert payload["linked_review_id"] == "review-bad-db"
    assert payload["event_id"] == "event-bad-db"
    assert payload["module"] == "review"


def _seed_run(session: Session, tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "run-bad-db"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": "run-bad-db", "video_id": "video-bad-db"}),
        encoding="utf-8",
    )
    VideoRepository(session).create(
        id="video-bad-db",
        filename="bad.mp4",
        storage_path="local_videos/bad.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-bad-db",
        video_id="video-bad-db",
        status="completed",
        result_dir=str(run_dir),
        artifact_index={},
    )
    EventRepository(session).create(
        id="event-bad-db",
        run_id="run-bad-db",
        video_id="video-bad-db",
        type="danger_zone_intrusion",
        status="false_positive",
        severity="high",
        frame_index=42,
        track_id="17",
        payload={},
    )
