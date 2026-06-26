from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from app.repositories import ProcessingTaskRepository, VideoRepository
from app.services.processing_service import processing_service


def test_processing_tasks_endpoint_reads_db_tasks_and_filters(
    tmp_path: Path,
) -> None:
    client, session_factory, cleanup = _client_with_session(tmp_path)
    try:
        with session_factory() as session:
            VideoRepository(session).create(
                id="video-processing-1",
                filename="traffic.mp4",
                storage_path="samples/videos/traffic.mp4",
                status="uploaded",
                fps=10.0,
                width=64,
                height=48,
                frame_count=2,
                duration_seconds=0.2,
            )
            VideoRepository(session).create(
                id="video-processing-2",
                filename="other.mp4",
                storage_path="samples/videos/other.mp4",
                status="uploaded",
                fps=10.0,
                width=64,
                height=48,
                frame_count=2,
                duration_seconds=0.2,
            )
            repo = ProcessingTaskRepository(session)
            repo.create(
                id="task-processing-1",
                video_id="video-processing-1",
                status="completed",
                mode="detection_tracking",
                parameters={"mode": "detection_tracking", "frame_stride": 1},
                progress=1.0,
                result={"run_id": "run-processing-1"},
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                finished_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=2),
            )
            repo.create(
                id="task-processing-2",
                video_id="video-processing-2",
                status="failed",
                mode="detection_only",
                parameters={"mode": "detection_only"},
                progress=0.5,
                result={"run_id": "run-processing-2"},
                error_message="detector unavailable",
                started_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
            session.commit()

        response = client.get("/api/processing/tasks")
        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload] == ["task-processing-1", "task-processing-2"]
        assert payload[0] == {
            "id": "task-processing-1",
            "video_id": "video-processing-1",
            "run_id": "run-processing-1",
            "task_type": "offline_process",
            "mode": "detection_tracking",
            "status": "completed",
            "params_json": {"mode": "detection_tracking", "frame_stride": 1},
            "progress": 1.0,
            "error_message": None,
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:02+00:00",
            "created_at": payload[0]["created_at"],
            "result": {"run_id": "run-processing-1"},
        }

        assert [
            item["id"]
            for item in client.get("/api/processing/tasks?video_id=video-processing-1").json()
        ] == ["task-processing-1"]
        assert [
            item["id"]
            for item in client.get("/api/processing/tasks?run_id=run-processing-2").json()
        ] == ["task-processing-2"]
        assert [
            item["id"]
            for item in client.get("/api/processing/tasks?status=completed").json()
        ] == ["task-processing-1"]
        assert [
            item["id"]
            for item in client.get("/api/processing/tasks?task_type=detection_only").json()
        ] == ["task-processing-2"]
        assert client.get("/api/processing/tasks?run_id=missing").json() == []
    finally:
        cleanup()


def test_processing_tasks_endpoint_returns_empty_list_for_empty_db(tmp_path: Path) -> None:
    client, _session_factory, cleanup = _client_with_session(tmp_path)
    try:
        response = client.get("/api/processing/tasks")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        cleanup()


def test_processing_tasks_endpoint_can_include_legacy_memory_tasks(
    tmp_path: Path,
) -> None:
    client, _session_factory, cleanup = _client_with_session(tmp_path)
    processing_service.clear()
    processing_service._tasks["memory-task-1"] = {
        "id": "memory-task-1",
        "video_id": "video-memory",
        "run_id": "run-memory",
        "task_type": "offline_process",
        "status": "completed",
        "params_json": {"mode": "detection_only"},
        "progress": 1.0,
        "error_message": None,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "created_at": "2026-01-01T00:00:00+00:00",
        "result": {"run_id": "run-memory"},
    }
    try:
        assert client.get("/api/processing/tasks").json() == []
        response = client.get("/api/processing/tasks?include_memory=true&run_id=run-memory")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "memory-task-1"
    finally:
        processing_service.clear()
        cleanup()


def _client_with_session(
    tmp_path: Path,
) -> tuple[TestClient, sessionmaker[Session], callable]:
    database_path = tmp_path / "processing-tasks.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    def cleanup() -> None:
        fastapi_app.dependency_overrides.pop(get_db, None)
        engine.dispose()

    return TestClient(fastapi_app), TestingSessionLocal, cleanup
