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
from app.repositories import ModelRunRepository
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


@pytest.fixture
def model_run_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    database_path = tmp_path / "model-runs.db"
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
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    monkeypatch.setenv("YOLO_MODEL_PATH", str(tmp_path / "secret-model-dir" / "best.pt"))
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app), TestingSessionLocal
    finally:
        fastapi_app.dependency_overrides.clear()
        engine.dispose()


def test_processing_writes_detector_and_tracker_model_runs(
    model_run_client: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
) -> None:
    client, session_factory = model_run_client
    source_video = _write_tiny_video(tmp_path / "tracking.mp4", frames=2)
    with source_video.open("rb") as file:
        upload_response = client.post(
            "/api/videos/upload",
            files={"file": ("tracking.mp4", file, "video/mp4")},
        )
    assert upload_response.status_code == 200
    video_id = upload_response.json()["id"]

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking",
            "dry_run": True,
            "tracker_dry_run": True,
            "frame_stride": 1,
            "max_frames": 1,
            "conf_threshold": 0.42,
            "deepsort_max_age": 12,
        },
    )
    assert process_response.status_code == 200
    run_id = process_response.json()["run_id"]

    with session_factory() as session:
        model_runs = ModelRunRepository(session).list(run_id=run_id)

    assert [model_run.task_type for model_run in model_runs] == ["detector", "tracker"]
    detector = model_runs[0]
    tracker = model_runs[1]
    assert detector.model_name == "yolov8"
    assert detector.model_version == "dry-run"
    assert detector.parameters["conf_threshold"] == 0.42
    assert detector.parameters["dry_run"] is True
    assert detector.parameters["model_path"] == "best.pt"
    assert str(tmp_path) not in str(detector.parameters)
    assert tracker.model_name == "deepsort"
    assert tracker.model_version == "dry-run"
    assert tracker.parameters["max_age"] == 12
    assert tracker.parameters["dry_run"] is True
    assert tracker.metrics["total_tracks"] == process_response.json()["total_tracks"]


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
