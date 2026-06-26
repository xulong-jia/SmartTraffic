from collections.abc import Generator
from contextlib import contextmanager
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.repositories import TrafficAnalysisRunRepository, VideoRepository


def test_report_bundle_includes_visual_artifact_references(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    _write_keyframe_index(tmp_path / "results" / "run-bundle")
    client = TestClient(app)
    with _db_session() as session:
        _seed_bundle_run(session)

    response = client.get("/api/reports/run-bundle/bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "full_stage_6cd.report_bundle.v1"
    assert payload["run_id"] == "run-bundle"
    assert payload["included_sections"] == [
        "summary",
        "events",
        "alerts",
        "flow_counts",
        "zone_statistics",
        "bad_cases",
        "evaluation_results",
        "keyframes",
        "annotated_video",
    ]
    references = {item["key"]: item for item in payload["artifact_references"]}
    assert references["keyframes"]["exists"] is True
    assert references["keyframes"]["path"] == "keyframes/index.json"
    assert references["annotated_video"]["exists"] is True
    assert references["annotated_video"]["path"] == "annotated_video.mp4"
    assert "/tmp/" not in response.text


def test_report_summary_includes_keyframe_and_video_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    _write_keyframe_index(tmp_path / "results" / "run-bundle")
    client = TestClient(app)
    with _db_session() as session:
        _seed_bundle_run(session)

    response = client.get("/api/reports/run-bundle/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["keyframe_summary"]["keyframe_count"] == 1
    assert payload["keyframe_summary"]["keyframe_items"][0]["path"] == (
        "keyframes/event_1.jpg"
    )
    assert payload["annotated_video"]["annotated_video_available"] is True
    assert payload["annotated_video"]["annotated_video_reference"] == "annotated_video.mp4"
    assert "/tmp/" not in response.text


def test_report_bundle_handles_missing_visual_artifacts_gracefully() -> None:
    client = TestClient(app)
    with _db_session() as session:
        _seed_missing_visual_run(session)

    response = client.get("/api/reports/run-no-visuals/bundle")

    assert response.status_code == 200
    references = {item["key"]: item for item in response.json()["artifact_references"]}
    assert references["keyframes"]["exists"] is False
    assert references["annotated_video"]["exists"] is False


@contextmanager
def _db_session() -> Generator[Session, None, None]:
    generator = app.dependency_overrides[get_db]()
    session = next(generator)
    try:
        yield session
        session.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def _write_keyframe_index(run_dir: Path) -> None:
    keyframes_dir = run_dir / "keyframes"
    keyframes_dir.mkdir(parents=True)
    (keyframes_dir / "index.json").write_text(
        json.dumps(
            {
                "schema_version": "stage6f.v1",
                "run_id": "run-bundle",
                "video_id": "video-bundle",
                "status": "available",
                "items": [
                    {
                        "source_type": "event",
                        "source_id": "event-1",
                        "frame_index": 12,
                        "timestamp_ms": 480,
                        "path": "keyframes/event_1.jpg",
                        "status": "available",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _seed_bundle_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-bundle",
        filename="bundle.mp4",
        storage_path="local_videos/bundle.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-bundle",
        video_id="video-bundle",
        status="completed",
        result_dir="results/traffic_analysis/run-bundle",
        artifact_index={
            "keyframes_index": "keyframes/index.json",
            "annotated_video": "annotated_video.mp4",
        },
        summary={
            "schema_version": "test.v1",
            "artifact_summary": {
                "keyframes": {
                    "status": "available",
                    "path": "keyframes/",
                    "record_count": 1,
                },
                "keyframes_index": {
                    "status": "available",
                    "path": "keyframes/index.json",
                    "record_count": 1,
                },
                "annotated_video": {
                    "status": "available",
                    "path": "annotated_video.mp4",
                    "record_count": 1,
                },
            },
        },
    )


def _seed_missing_visual_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-no-visuals",
        filename="missing.mp4",
        storage_path="local_videos/missing.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-no-visuals",
        video_id="video-no-visuals",
        status="completed",
        result_dir="results/traffic_analysis/run-no-visuals",
        artifact_index={},
        summary={"schema_version": "test.v1", "artifact_summary": {}},
    )
