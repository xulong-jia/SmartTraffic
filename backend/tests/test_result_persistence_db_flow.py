from collections.abc import Generator
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
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
    DetectionRepository,
    FlowCountRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    ZoneStatisticRepository,
)
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage2cd.db'}",
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
    monkeypatch.setattr(
        "app.services.processing_service.TrajectoryService",
        _FakeTrajectoryServiceWithCoreArtifacts,
    )
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


def test_processing_persists_core_results_to_db_and_keeps_artifacts(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    source_video = _write_tiny_video(tmp_path / "upload.mp4")
    with source_video.open("rb") as file:
        upload_response = client.post(
            "/api/videos/upload",
            files={"file": ("upload.mp4", file, "video/mp4")},
        )
    assert upload_response.status_code == 200
    video_id = upload_response.json()["id"]

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking_trajectory",
            "detector_dry_run": True,
            "tracker_dry_run": True,
            "run_events": False,
        },
    )

    assert process_response.status_code == 200
    run_id = process_response.json()["run_id"]
    run_dir = tmp_path / "results" / run_id
    assert (run_dir / "detections.csv").is_file()
    assert (run_dir / "tracks.csv").is_file()
    assert (run_dir / "trajectory_points.csv").is_file()
    assert (run_dir / "flow_counts.json").is_file()
    assert (run_dir / "zone_statistics.json").is_file()

    with session_factory() as session:
        run = TrafficAnalysisRunRepository(session).get(run_id)
        assert run is not None
        assert run.video_id == video_id
        assert run.artifact_index["detections_csv"] == "detections.csv"

        detections = DetectionRepository(session).list(run_id=run_id)
        assert len(detections) == 1
        assert detections[0].class_name == "car"
        assert detections[0].bbox == {"x1": 10.0, "y1": 11.0, "x2": 30.0, "y2": 31.0}

        tracks = TrackRepository(session).list(run_id=run_id)
        assert len(tracks) == 1
        assert tracks[0].track_id == "7"

        trajectory_points = TrajectoryPointRepository(session).list(run_id=run_id)
        assert len(trajectory_points) == 1
        assert trajectory_points[0].track_id == "7"
        assert trajectory_points[0].x == 20.0
        assert trajectory_points[0].y == 21.0

        flow_counts = FlowCountRepository(session).list(run_id=run_id)
        assert len(flow_counts) == 1
        assert flow_counts[0].line_id == "line-main"
        assert flow_counts[0].count == 3

        zone_statistics = ZoneStatisticRepository(session).list(run_id=run_id)
        assert len(zone_statistics) == 1
        assert zone_statistics[0].metric_name == "vehicle_count"
        assert zone_statistics[0].metric_value == 2.0


class _FakeTrajectoryServiceWithCoreArtifacts:
    def __init__(self, results_dir: str | Path | None = None, **_: Any) -> None:
        self.results_dir = Path(results_dir) if results_dir is not None else None

    def run_trajectory(
        self,
        *,
        video_id: str,
        video_path: str | Path,
        run_id: str | None = None,
        params: Any = None,
    ) -> dict[str, Any]:
        del params
        effective_run_id = run_id or "run_stage2cd"
        writer = TrafficArtifactWriter(self.results_dir or Path(video_path).parent)
        run_dir = writer.create_run_directory(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "stage": "stage_4_trajectory_engine",
                "next_stage": "stage_5_event_engine_not_started",
            },
        )
        detection_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [10, 11, 30, 31],
                    }
                ],
            }
        ]
        tracking_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "tracks": [
                    {
                        "track_id": 7,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [10, 11, 30, 31],
                        "center": [20, 21],
                        "state": "confirmed",
                    }
                ],
            }
        ]
        trajectory_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "trajectory_points": [
                    {
                        "track_id": 7,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [10, 11, 30, 31],
                        "center": [20, 21],
                        "bottom_center": [20, 31],
                        "state": "confirmed",
                        "speed_px_per_second": 4.5,
                        "moving_angle": 90,
                    }
                ],
            }
        ]
        writer.write_detection_outputs(effective_run_id, video_id, detection_frames)
        writer.write_tracking_outputs(effective_run_id, video_id, tracking_frames)
        writer.write_trajectory_outputs(effective_run_id, video_id, trajectory_frames)
        _write_json(
            run_dir / "flow_counts.json",
            {
                "records": [
                    {
                        "counting_line_id": "line-main",
                        "class_name": "car",
                        "direction": "positive",
                        "total_count": 3,
                    }
                ]
            },
        )
        _write_json(
            run_dir / "zone_statistics.json",
            {
                "windows": [
                    {
                        "zone_id": "zone-main",
                        "metric_name": "vehicle_count",
                        "metric_value": 2,
                    }
                ],
                "congestion_events": [],
            },
        )
        artifacts = writer.artifact_index(effective_run_id)
        writer.update_metadata(
            effective_run_id,
            {
                "video_id": video_id,
                "status": "completed",
                "artifacts": artifacts,
            },
        )
        writer.write_run_manifest(effective_run_id, status="completed")
        return {
            "run_id": effective_run_id,
            "video_id": video_id,
            "status": "completed",
            "stage": "stage_4_trajectory_engine",
            "next_stage": "stage_5_event_engine_not_started",
            "total_frames_processed": 1,
            "total_detections": 1,
            "total_tracks": 1,
            "unique_track_ids": 1,
            "total_trajectory_points": 1,
            "per_class_counts": {"car": 1},
            "per_class_track_counts": {"car": 1},
            "track_state_counts": {"confirmed": 1},
            "trajectory_track_state_counts": {"confirmed": 1},
            "avg_track_length": 1.0,
            "max_track_length": 1,
            "avg_speed_px_per_second": 4.5,
            "result_dir": str(run_dir),
            "artifacts": artifacts,
        }


def _write_tiny_video(path: Path) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
