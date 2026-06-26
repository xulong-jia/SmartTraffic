from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
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
    VideoRepository,
    ZoneStatisticRepository,
)
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'analysis-index.db'}",
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


def test_analysis_runs_api_uses_db_index_without_artifact_directory(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_db_run(session)
        session.commit()

    list_response = client.get("/api/analysis-runs")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["run_id"] == "run-db-index"
    assert list_payload["items"][0]["source"] == "db"

    detail_response = client.get("/api/analysis-runs/run-db-index")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["run_id"] == "run-db-index"
    assert detail_payload["source"] == "db"
    assert detail_payload["artifact_index"]["status"] == "available"

    manifest_response = client.get("/api/analysis-runs/run-db-index/manifest")
    assert manifest_response.status_code == 200
    manifest_payload = manifest_response.json()
    assert manifest_payload["run_id"] == "run-db-index"
    assert manifest_payload["source"] == "db"
    assert manifest_payload["artifacts"]["detections_csv"]["path"] == "detections.csv"

    detections_response = client.get("/api/analysis-runs/run-db-index/detections")
    assert detections_response.status_code == 200
    assert detections_response.json()["source"] == "db"
    assert detections_response.json()["rows"][0]["class_name"] == "car"

    tracks_response = client.get("/api/analysis-runs/run-db-index/tracks")
    assert tracks_response.status_code == 200
    assert tracks_response.json()["source"] == "db"
    assert tracks_response.json()["rows"][0]["track_id"] == "1"

    trajectory_response = client.get(
        "/api/analysis-runs/run-db-index/trajectory-points?track_id=1"
    )
    assert trajectory_response.status_code == 200
    assert trajectory_response.json()["source"] == "db"
    assert trajectory_response.json()["rows"][0]["track_id"] == "1"

    flow_response = client.get("/api/analysis-runs/run-db-index/flow-counts")
    assert flow_response.status_code == 200
    assert flow_response.json()["source"] == "db"
    assert flow_response.json()["records"][0]["count"] == 2

    zone_response = client.get("/api/analysis-runs/run-db-index/zone-statistics")
    assert zone_response.status_code == 200
    assert zone_response.json()["source"] == "db"
    assert zone_response.json()["windows"][0]["metric_name"] == "vehicle_count"


def test_analysis_runs_api_falls_back_to_artifacts_when_db_missing(
    client: TestClient,
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(
        "run-artifact-only",
        {
            "video_id": "video-artifact",
            "status": "completed",
            "stage": "stage_2_yolov8_detection",
        },
    )
    writer.write_detection_outputs(
        "run-artifact-only",
        "video-artifact",
        [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "truck",
                        "confidence": 0.8,
                        "bbox": [1, 2, 3, 4],
                    }
                ],
            }
        ],
    )
    writer.write_run_manifest("run-artifact-only", status="completed")

    response = client.get("/api/analysis-runs/run-artifact-only/detections")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "artifact"
    assert payload["rows"][0]["class_name"] == "truck"


def _seed_db_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-db-index",
        filename="db-index.mp4",
        storage_path="local_videos/db-index.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-db-index",
        video_id="video-db-index",
        status="completed",
        result_dir="results/traffic_analysis/run-db-index",
        artifact_index={
            "detections_csv": "detections.csv",
            "tracks_csv": "tracks.csv",
            "trajectory_points_csv": "trajectory_points.csv",
            "flow_counts": "flow_counts.json",
            "zone_statistics": "zone_statistics.json",
        },
        summary={"stage": "stage_4_trajectory_engine"},
    )
    DetectionRepository(session).create(
        id="det-db-1",
        run_id="run-db-index",
        video_id="video-db-index",
        frame_index=1,
        class_name="car",
        confidence=0.91,
        bbox={"x1": 1, "y1": 2, "x2": 3, "y2": 4},
    )
    TrackRepository(session).create(
        id="track-db-1",
        run_id="run-db-index",
        video_id="video-db-index",
        track_id="1",
        class_name="car",
        start_frame=1,
        end_frame=3,
        confidence=0.88,
        metadata_json={"state": "confirmed"},
    )
    TrajectoryPointRepository(session).create(
        id="traj-db-1",
        run_id="run-db-index",
        video_id="video-db-index",
        track_id="1",
        frame_index=1,
        timestamp_ms=100.0,
        x=12.0,
        y=24.0,
        speed=7.5,
        direction="90",
        features={"state": "confirmed"},
    )
    FlowCountRepository(session).create(
        id="flow-db-1",
        run_id="run-db-index",
        line_id="line-a",
        class_name="car",
        direction="positive",
        count=2,
    )
    ZoneStatisticRepository(session).create(
        id="zone-stat-db-1",
        run_id="run-db-index",
        metric_name="vehicle_count",
        metric_value=3.0,
        payload={"zone_id": "zone-a"},
    )
