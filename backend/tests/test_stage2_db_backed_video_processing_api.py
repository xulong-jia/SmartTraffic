from collections.abc import Generator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from app.repositories import (
    FrameRepository,
    ProcessingTaskRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    database_path = tmp_path / "stage2ab.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
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
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


def test_video_upload_list_detail_status_and_frames_are_db_backed(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    source_video = _write_tiny_video(tmp_path / "upload.mp4", frames=3)

    with source_video.open("rb") as file:
        upload_response = client.post(
            "/api/videos/upload",
            files={"file": ("upload.mp4", file, "video/mp4")},
        )

    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    video_id = uploaded["id"]
    assert uploaded["status"] == "uploaded"

    with session_factory() as session:
        video = VideoRepository(session).get(video_id)
        assert video is not None
        assert video.filename == "upload.mp4"
        assert video.storage_path.endswith("upload.mp4")
        assert video.frame_count == 3

        FrameRepository(session).bulk_create(
            [
                {
                    "id": "frame-stage2ab-1",
                    "video_id": video_id,
                    "frame_index": 0,
                    "timestamp_ms": 0.0,
                    "image_path": "frames/000000.jpg",
                    "metadata_json": {"source": "test"},
                },
                {
                    "id": "frame-stage2ab-2",
                    "video_id": video_id,
                    "frame_index": 2,
                    "timestamp_ms": 200.0,
                    "image_path": "frames/000002.jpg",
                    "metadata_json": {"source": "test"},
                },
            ]
        )
        session.commit()

    list_response = client.get("/api/videos")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [video_id]

    detail_response = client.get(f"/api/videos/{video_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["total_frames"] == 3

    status_response = client.get(f"/api/videos/{video_id}/status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "video_id": video_id,
        "status": "uploaded",
        "latest_task": None,
    }

    frames_response = client.get(f"/api/videos/{video_id}/frames")
    assert frames_response.status_code == 200
    assert [frame["frame_index"] for frame in frames_response.json()] == [0, 2]


def test_processing_creates_db_tasks_and_multiple_runs_for_one_video(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    source_video = _write_tiny_video(tmp_path / "process.mp4", frames=2)
    with source_video.open("rb") as file:
        upload_response = client.post(
            "/api/videos/upload",
            files={"file": ("process.mp4", file, "video/mp4")},
        )
    assert upload_response.status_code == 200
    video_id = upload_response.json()["id"]

    process_payload = {
        "mode": "detection_only",
        "dry_run": True,
        "frame_stride": 1,
        "max_frames": 1,
    }
    first_response = client.post(f"/api/videos/{video_id}/process", json=process_payload)
    second_response = client.post(f"/api/videos/{video_id}/process", json=process_payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_run_id = first_response.json()["run_id"]
    second_run_id = second_response.json()["run_id"]
    assert first_run_id != second_run_id

    with session_factory() as session:
        video = VideoRepository(session).get(video_id)
        assert video is not None
        assert video.status == "completed"

        tasks = ProcessingTaskRepository(session).list(video_id=video_id)
        assert [task.status for task in tasks] == ["completed", "completed"]
        assert [task.progress for task in tasks] == [1.0, 1.0]
        assert all(task.started_at is not None for task in tasks)
        assert all(task.finished_at is not None for task in tasks)
        assert {task.result["run_id"] for task in tasks} == {first_run_id, second_run_id}

        runs = TrafficAnalysisRunRepository(session).list(video_id=video_id)
        assert {run.id for run in runs} == {first_run_id, second_run_id}
        assert all(run.status == "completed" for run in runs)
        assert all(run.artifact_index for run in runs)

    status_response = client.get(f"/api/videos/{video_id}/status")
    assert status_response.status_code == 200
    latest_task = status_response.json()["latest_task"]
    assert latest_task["status"] == "completed"
    assert latest_task["result"]["run_id"] == second_run_id


def _write_tiny_video(path: Path, *, frames: int) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for _ in range(frames):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    return path
