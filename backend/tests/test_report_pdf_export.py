from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.repositories import TrafficAnalysisRunRepository, VideoRepository


def test_report_pdf_export_returns_pdf_with_disclaimer() -> None:
    client = TestClient(app)
    with _db_session() as session:
        _seed_pdf_run(session)

    response = client.get("/api/reports/run-pdf/export.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == (
        'attachment; filename="smarttraffic_report_run-pdf.pdf"'
    )
    assert response.content.startswith(b"%PDF-1.4")
    assert b"SmartTraffic Analysis Report" in response.content
    assert b"It is not a traffic enforcement document." in response.content
    assert b"Metrics depend on available annotations and configuration." in response.content


def test_report_pdf_export_missing_run_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/reports/missing-run/export.pdf")

    assert response.status_code == 404


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


def _seed_pdf_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-pdf",
        filename="pdf.mp4",
        storage_path="local_videos/pdf.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-pdf",
        video_id="video-pdf",
        status="completed",
        result_dir="results/traffic_analysis/run-pdf",
        artifact_index={},
        summary={
            "schema_version": "test.v1",
            "artifact_summary": {
                "keyframes": {
                    "status": "empty",
                    "path": "keyframes/",
                    "record_count": 0,
                },
                "annotated_video": {
                    "status": "missing_source_video",
                    "path": "annotated_video.mp4",
                    "record_count": 0,
                },
            },
        },
    )
