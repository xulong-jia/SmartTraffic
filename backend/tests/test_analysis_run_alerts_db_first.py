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
from app.repositories import TrafficAnalysisRunRepository, VideoRepository
from app.services.event_lifecycle_service import EventLifecycleService


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'analysis-run-alerts.db'}",
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


def test_analysis_run_alerts_reads_db_first_without_artifacts(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _seed_run(session, run_id="run-alerts-db", video_id="video-alerts-db")
        event = EventLifecycleService(session).create_event_with_evidence(
            run_id="run-alerts-db",
            video_id="video-alerts-db",
            event_id="event-alerts-db-1",
            event_type="wrong_way_driving",
            status="pending",
            severity="high",
            track_id="12",
            frame_index=42,
            payload={},
        )
        alert = EventLifecycleService(session).create_alert_for_event(event["id"])
        session.commit()

    response = client.get("/api/analysis-runs/run-alerts-db/alerts?level=critical")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-alerts-db"
    assert payload["video_id"] == "video-alerts-db"
    assert payload["source"] == "db"
    assert payload["limit"] == 100
    assert payload["level"] == "critical"
    assert payload["status"] is None
    assert payload["event_type"] is None
    assert payload["summary"]["total_alerts"] == 1
    assert payload["alerts"][0]["id"] == alert["id"]
    assert payload["alerts"][0]["event_id"] == "event-alerts-db-1"
    assert payload["alerts"][0]["level"] == "critical"


def test_analysis_run_alerts_falls_back_to_artifacts_when_db_has_no_alerts(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    with session_factory() as session:
        _seed_run(session, run_id="run-alerts-artifact", video_id="video-artifact")
        session.commit()
    _write_alert_artifacts(tmp_path, run_id="run-alerts-artifact")

    response = client.get("/api/analysis-runs/run-alerts-artifact/alerts?status=new")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-alerts-artifact"
    assert payload["source"] == "artifact"
    assert payload["summary"]["total_alerts"] == 1
    assert payload["alerts"][0]["event_id"] == "event-artifact-1"
    assert payload["alerts"][0]["status"] == "new"


def test_analysis_run_alerts_missing_run_still_returns_404(client: TestClient) -> None:
    response = client.get("/api/analysis-runs/missing-alert-run/alerts")

    assert response.status_code == 404
    assert response.json()["error_code"] == "not_found"


def _seed_run(session: Session, *, run_id: str, video_id: str) -> None:
    VideoRepository(session).create(
        id=video_id,
        filename=f"{video_id}.mp4",
        storage_path=f"local_videos/{video_id}.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id=run_id,
        video_id=video_id,
        status="completed",
        result_dir=f"results/traffic_analysis/{run_id}",
        artifact_index={},
    )


def _write_alert_artifacts(tmp_path: Path, *, run_id: str) -> None:
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video-artifact",
            "stage": "stage_5_alert_center",
            "artifacts": {"alerts": "alerts.jsonl"},
        },
    )
    writer.write_alert_outputs(
        run_id=run_id,
        video_id="video-artifact",
        alerts=[
            {
                "id": "alert-artifact-1",
                "alert_id": "alert-artifact-1",
                "event_id": "event-artifact-1",
                "run_id": run_id,
                "video_id": "video-artifact",
                "alert_type": "danger_zone_intrusion",
                "event_type": "danger_zone_intrusion",
                "level": "critical",
                "status": "new",
                "message": "danger zone intrusion event detected",
                "title": "Danger zone intrusion",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )
