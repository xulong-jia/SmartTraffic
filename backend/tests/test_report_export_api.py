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


def test_report_exports_use_latest_evaluation_run_for_summaries() -> None:
    client = TestClient(app)
    with _db_session() as session:
        _seed_latest_evaluation_report_run(session)

    summary_response = client.get("/api/reports/run-report-latest/summary")
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert summary["counts"]["evaluation_results_count"] == 10
    assert summary["latest_evaluation_run_id"] == "evalrun-report-new"
    assert summary["evaluation_metric_summary"] == {
        "event_accuracy": 1.0,
        "event_precision": 1.0,
        "event_recall": 1.0,
        "event_f1": 1.0,
        "false_alarm_rate": 0.0,
    }
    assert summary["evaluation_summary"]["metrics"] == summary["latest_evaluation_metrics"]
    assert len(summary["latest_evaluation_results"]) == 5

    json_response = client.get("/api/reports/run-report-latest/export.json")
    assert json_response.status_code == 200, json_response.text
    payload = json_response.json()
    assert len(payload["evaluation_results"]) == 10
    assert payload["latest_evaluation_run_id"] == "evalrun-report-new"
    assert payload["latest_evaluation_metrics"]["event_accuracy"] == 1.0
    assert payload["latest_evaluation_metrics"]["false_alarm_rate"] == 0.0
    assert {item["evaluation_run_id"] for item in payload["latest_evaluation_results"]} == {
        "evalrun-report-new"
    }

    pdf_response = client.get("/api/reports/run-report-latest/export.pdf")
    assert pdf_response.status_code == 200, pdf_response.text
    assert b"event_accuracy': 1.0" in pdf_response.content
    assert b"event_precision': 1.0" in pdf_response.content
    assert b"event_recall" in pdf_response.content
    assert b"event_f1" in pdf_response.content
    assert b"false_alarm_rate" in pdf_response.content
    assert b"None" not in pdf_response.content


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


def _seed_latest_evaluation_report_run(session: Session) -> None:
    VideoRepository(session).create(
        id="video-report-latest",
        filename="latest.mp4",
        storage_path="local_videos/latest.mp4",
        status="uploaded",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-report-latest",
        video_id="video-report-latest",
        status="completed",
        result_dir="/tmp/smarttraffic/run-report-latest",
        artifact_index={},
        summary={"schema_version": "test.v1", "artifact_summary": {}},
    )
    EvaluationDatasetRepository(session).create(
        id="dataset-report-latest",
        name="Latest Report Dataset",
        dataset_type="event",
        status="active",
        config={"source": "test"},
    )
    old_time = datetime(2026, 1, 1, tzinfo=UTC)
    new_time = datetime(2026, 1, 2, tzinfo=UTC)
    metrics = [
        "event_accuracy",
        "event_precision",
        "event_recall",
        "event_f1",
        "false_alarm_rate",
    ]
    for index, metric_name in enumerate(metrics):
        _create_report_evaluation_result(
            session,
            result_id=f"eval-result-report-old-{index}",
            evaluation_run_id="evalrun-report-old",
            metric_name=metric_name,
            metric_value=None,
            status="not_applicable",
            timestamp=old_time,
        )
    latest_values = {
        "event_accuracy": 1.0,
        "event_precision": 1.0,
        "event_recall": 1.0,
        "event_f1": 1.0,
        "false_alarm_rate": 0.0,
    }
    for index, (metric_name, metric_value) in enumerate(latest_values.items()):
        _create_report_evaluation_result(
            session,
            result_id=f"eval-result-report-new-{index}",
            evaluation_run_id="evalrun-report-new",
            metric_name=metric_name,
            metric_value=metric_value,
            status="available",
            timestamp=new_time,
        )


def _create_report_evaluation_result(
    session: Session,
    *,
    result_id: str,
    evaluation_run_id: str,
    metric_name: str,
    metric_value: float | None,
    status: str,
    timestamp: datetime,
) -> None:
    EvaluationResultRepository(session).create(
        id=result_id,
        dataset_id="dataset-report-latest",
        run_id="run-report-latest",
        evaluation_type="event",
        status="completed",
        created_at=timestamp,
        metrics={
            "metric_name": metric_name,
            "metric_value": metric_value,
            "details": {"status": status, "reason": "missing expected events" if metric_value is None else None},
        },
        summary={
            "evaluation_run": {
                "evaluation_run_id": evaluation_run_id,
                "dataset_id": "dataset-report-latest",
                "run_id": "run-report-latest",
                "evaluation_type": "event",
                "status": "completed",
                "started_at": timestamp.isoformat(),
                "finished_at": timestamp.isoformat(),
                "config": {},
            }
        },
    )
