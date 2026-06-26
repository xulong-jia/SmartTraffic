from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
import csv
import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.repositories import (
    BadCaseRepository,
    EvaluationDatasetRepository,
    EvaluationResultRepository,
    FlowCountRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
    ZoneStatisticRepository,
)
from app.services.event_lifecycle_service import EventLifecycleService


def test_report_runs_summary_json_and_csv_exports() -> None:
    client = TestClient(app)
    with _db_session() as session:
        _seed_report_run(session)

    runs_response = client.get("/api/reports/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["items"][0]["run_id"] == "run-report-db"

    summary_response = client.get("/api/reports/run-report-db/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["counts"]["events_count"] == 1
    assert summary["counts"]["alerts_count"] == 1
    assert summary["counts"]["flow_count_records"] == 1
    assert summary["counts"]["zone_statistics_records"] == 1
    assert summary["counts"]["bad_cases_count"] == 1
    assert summary["counts"]["evaluation_results_count"] == 1
    assert summary["run"]["result_dir"] == "results/traffic_analysis/run-report-db"
    assert "not for traffic enforcement" in summary["note"]

    json_response = client.get("/api/reports/run-report-db/export.json")
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["metadata"]["schema_version"] == "full_stage_6ab.report.v1"
    assert payload["events"][0]["event_id"] == "event-report-1"
    assert payload["alerts"][0]["event_id"] == "event-report-1"
    assert payload["bad_cases"][0]["case_id"] == "badcase-report-1"
    assert payload["evaluation_results"][0]["metric_name"] == "event_precision"

    expected_values = {
        "events": "wrong_way_driving",
        "alerts": "wrong_way_driving event detected",
        "flow_counts": "northbound",
        "zone_statistics": "occupancy_count",
        "bad_cases": "false_positive",
        "evaluation_results": "event_precision",
    }
    for section, expected_value in expected_values.items():
        csv_response = client.get(
            f"/api/reports/run-report-db/export.csv?section={section}"
        )
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"].startswith("text/csv")
        assert (
            'attachment; filename="smarttraffic_run-report-db_'
            in csv_response.headers["content-disposition"]
        )
        rows = list(csv.reader(io.StringIO(csv_response.text)))
        assert rows[0]
        assert expected_value in csv_response.text


def test_report_export_returns_header_for_empty_sections() -> None:
    client = TestClient(app)
    with _db_session() as session:
        _seed_empty_run(session)
    with _db_session() as session:
        assert TrafficAnalysisRunRepository(session).get("run-empty-report") is not None

    runs_response = client.get("/api/reports/runs")
    assert runs_response.status_code == 200
    assert "run-empty-report" in [item["run_id"] for item in runs_response.json()["items"]]
    summary_response = client.get("/api/reports/run-empty-report/summary")
    assert summary_response.status_code == 200, summary_response.text

    response = client.get("/api/reports/run-empty-report/export.csv?section=events")

    assert response.status_code == 200, response.text
    assert response.text == (
        "event_id,run_id,event_type,status,severity,track_id,zone_id,frame_index,"
        "timestamp_ms\r\n"
    )


def test_report_export_rejects_missing_run_and_unknown_section() -> None:
    client = TestClient(app)

    missing_response = client.get("/api/reports/missing-run/summary")
    invalid_section_response = client.get(
        "/api/reports/missing-run/export.csv?section=pdf"
    )

    assert missing_response.status_code == 404
    assert invalid_section_response.status_code == 400


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


def _seed_empty_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-empty-report",
        filename="empty.mp4",
        storage_path="local_videos/empty.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-empty-report",
        video_id="video-empty-report",
        status="completed",
        result_dir="/tmp/smarttraffic/run-empty-report",
        artifact_index={},
        summary={"schema_version": "test.v1"},
    )


def _seed_report_run(session: Session) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    VideoRepository(session).create(
        id="video-report-1",
        filename="report.mp4",
        storage_path="local_videos/report.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-report-db",
        video_id="video-report-1",
        status="completed",
        result_dir="/tmp/smarttraffic/run-report-db",
        artifact_index={"events": "/tmp/smarttraffic/run-report-db/events.jsonl"},
        summary={
            "schema_version": "test.v1",
            "artifact_summary": {
                "detections": {"status": "available", "path": "detections.csv", "record_count": 2},
                "tracks": {"status": "available", "path": "tracks.csv", "record_count": 1},
                "trajectory_points": {
                    "status": "available",
                    "path": "trajectory_points.csv",
                    "record_count": 3,
                },
            },
        },
    )
    lifecycle = EventLifecycleService(session)
    lifecycle.create_event_with_evidence(
        run_id="run-report-db",
        video_id="video-report-1",
        event_id="event-report-1",
        event_type="wrong_way_driving",
        status="confirmed",
        severity="high",
        track_id="track-1",
        frame_index=12,
        timestamp_ms=480.0,
        zone_id=None,
        payload={"source": "test"},
    )
    lifecycle.create_alert_for_event("event-report-1")
    FlowCountRepository(session).create(
        id="flow-report-1",
        run_id="run-report-db",
        line_id="line-a",
        class_name="car",
        direction="northbound",
        count=4,
        window_start=now,
        window_end=now,
    )
    ZoneStatisticRepository(session).create(
        id="zone-stat-report-1",
        run_id="run-report-db",
        zone_id=None,
        metric_name="occupancy_count",
        metric_value=2.0,
        payload={"source": "test"},
    )
    BadCaseRepository(session).create(
        id="badcase-report-1",
        run_id="run-report-db",
        event_id="event-report-1",
        type="false_positive",
        status="open",
        severity="medium",
        description="Report bad case",
        tags=["report"],
        payload={
            "case_id": "badcase-report-1",
            "case_type": "false_positive",
            "module": "review_center",
            "source": "review_center",
        },
    )
    EvaluationDatasetRepository(session).create(
        id="dataset-report-1",
        name="Report Dataset",
        dataset_type="event",
        status="active",
        config={"source": "test"},
    )
    EvaluationResultRepository(session).create(
        id="eval-result-report-1",
        dataset_id="dataset-report-1",
        run_id="run-report-db",
        evaluation_type="event",
        status="completed",
        metrics={
            "metric_name": "event_precision",
            "metric_value": 1.0,
            "details": {"status": "available"},
        },
        summary={
            "evaluation_run": {
                "evaluation_run_id": "eval-run-report-1",
                "dataset_id": "dataset-report-1",
                "run_id": "run-report-db",
                "evaluation_type": "event",
                "status": "completed",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:00+00:00",
                "config": {},
            }
        },
    )
