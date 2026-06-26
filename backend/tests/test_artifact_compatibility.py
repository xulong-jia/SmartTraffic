import csv
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analysis.artifact_compatibility import (
    discover_run_artifacts,
    import_run_artifacts_to_db,
    list_alerts_read_through,
    list_detections_read_through,
    list_events_read_through,
    list_tracks_read_through,
)
from app.db.base import Base
import app.models  # noqa: F401
from app.repositories import (
    AlertRepository,
    DetectionRepository,
    EvaluationResultRepository,
    EventRepository,
    FlowCountRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    ZoneStatisticRepository,
)


def _session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def _write_tiny_run(tmp_path: Path, run_id: str = "run-compat") -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": "video-compat",
                "status": "completed",
                "input_video": "local_videos/demo.mp4",
                "artifacts": {
                    "detections_csv": "detections.csv",
                    "tracks_csv": "tracks.csv",
                    "trajectory_points_csv": "trajectory_points.csv",
                    "events_jsonl": "events.jsonl",
                    "alerts_jsonl": "alerts.jsonl",
                    "flow_counts": "flow_counts.json",
                    "zone_statistics": "zone_statistics.json",
                    "evaluation_summary": "evaluation_summary.json",
                    "bad_cases": "bad_cases.jsonl",
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "status": "completed", "artifacts": {}}),
        encoding="utf-8",
    )
    (run_dir / "artifact_index.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "artifacts": {
                    "detections_csv": "detections.csv",
                    "tracks_csv": "tracks.csv",
                    "events_jsonl": "events.jsonl",
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        run_dir / "detections.csv",
        [
            {
                "run_id": run_id,
                "video_id": "video-compat",
                "frame_index": "1",
                "timestamp_ms": "40",
                "class_name": "car",
                "confidence": "0.91",
                "x1": "1",
                "y1": "2",
                "x2": "3",
                "y2": "4",
            }
        ],
    )
    _write_csv(
        run_dir / "tracks.csv",
        [
            {
                "run_id": run_id,
                "video_id": "video-compat",
                "frame_index": "1",
                "timestamp_ms": "40",
                "track_id": "track-1",
                "class_name": "car",
                "confidence": "0.88",
                "x1": "1",
                "y1": "2",
                "x2": "3",
                "y2": "4",
                "state": "confirmed",
            }
        ],
    )
    _write_csv(
        run_dir / "trajectory_points.csv",
        [
            {
                "run_id": run_id,
                "video_id": "video-compat",
                "track_id": "track-1",
                "frame_index": "1",
                "timestamp_ms": "40",
                "center_x": "20.5",
                "center_y": "30.5",
                "speed_px_per_second": "8.5",
                "moving_angle": "90",
            }
        ],
    )
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {
                "event_id": "event-1",
                "run_id": run_id,
                "video_id": "video-compat",
                "event_type": "wrong_way_driving",
                "status": "new",
                "severity": "high",
                "frame_index": 1,
                "track_id": "track-1",
            }
        ],
    )
    _write_jsonl(
        run_dir / "alerts.jsonl",
        [
            {
                "alert_id": "alert-1",
                "run_id": run_id,
                "event_id": "event-1",
                "alert_type": "wrong_way_driving",
                "status": "new",
                "severity": "high",
                "message": "Wrong way detected",
            }
        ],
    )
    (run_dir / "flow_counts.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "zone_id": "zone-a",
                        "counting_line_id": "line-1",
                        "class_name": "car",
                        "direction": "in",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "zone_statistics.json").write_text(
        json.dumps(
            {
                "windows": [
                    {
                        "zone_id": "zone-a",
                        "vehicle_count": 2,
                        "avg_speed_px_per_frame": 3.5,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "evaluation_summary.json").write_text(
        json.dumps({"run_id": run_id, "summary": {"event": {"precision": 1.0}}}),
        encoding="utf-8",
    )
    _write_jsonl(
        run_dir / "bad_cases.jsonl",
        [
            {
                "case_id": "bad-1",
                "run_id": run_id,
                "event_id": "event-1",
                "case_type": "false_positive",
                "status": "open",
                "description": "Wrong event",
                "tags": ["review"],
            }
        ],
    )
    return run_dir


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_discovery_reports_existing_and_missing_artifacts(tmp_path):
    run_dir = _write_tiny_run(tmp_path)
    (run_dir / "alerts.jsonl").unlink()

    discovery = discover_run_artifacts("run-compat", result_dir=run_dir)

    assert discovery.run_id == "run-compat"
    assert discovery.paths["metadata"].exists is True
    assert discovery.paths["detections_csv"].exists is True
    assert discovery.paths["alerts_jsonl"].exists is False
    assert "alerts_jsonl" in discovery.missing


def test_dry_run_import_counts_without_writing(tmp_path):
    run_dir = _write_tiny_run(tmp_path)
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        summary = import_run_artifacts_to_db(session, "run-compat", run_dir, dry_run=True)

        assert summary.dry_run is True
        assert summary.planned["detections"] == 1
        assert summary.planned["tracks"] == 1
        assert summary.planned["events"] == 1
        assert DetectionRepository(session).list(run_id="run-compat") == []
        assert TrafficAnalysisRunRepository(session).get("run-compat") is None


def test_import_tiny_artifacts_is_idempotent(tmp_path):
    run_dir = _write_tiny_run(tmp_path)
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        first = import_run_artifacts_to_db(session, "run-compat", run_dir)
        second = import_run_artifacts_to_db(session, "run-compat", run_dir)

        assert first.imported["runs"] == 1
        assert second.skipped["runs"] == 1
        assert len(DetectionRepository(session).list(run_id="run-compat")) == 1
        assert len(TrackRepository(session).list(run_id="run-compat")) == 1
        assert len(TrajectoryPointRepository(session).list(run_id="run-compat")) == 1
        assert len(EventRepository(session).list(run_id="run-compat")) == 1
        assert len(AlertRepository(session).list(run_id="run-compat")) == 1
        assert len(FlowCountRepository(session).list(run_id="run-compat")) == 1
        assert len(ZoneStatisticRepository(session).list(run_id="run-compat")) == 1
        assert len(EvaluationResultRepository(session).list(run_id="run-compat")) == 1


def test_read_through_prefers_db_then_falls_back_to_artifact(tmp_path):
    run_dir = _write_tiny_run(tmp_path)
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        artifact_result = list_detections_read_through(session, "run-compat", run_dir)
        assert artifact_result.source == "artifact"
        assert artifact_result.items[0]["class_name"] == "car"

        import_run_artifacts_to_db(session, "run-compat", run_dir)
        db_result = list_detections_read_through(session, "run-compat", run_dir)
        assert db_result.source == "db"
        assert db_result.items[0]["class_name"] == "car"


def test_read_through_empty_when_db_and_artifact_missing(tmp_path):
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        result = list_tracks_read_through(session, "missing", tmp_path / "missing")

        assert result.source == "empty"
        assert result.items == []
        assert result.warnings


def test_read_through_jsonl_parse_error_returns_warning(tmp_path):
    run_dir = tmp_path / "bad-jsonl"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text("{not-json}\n", encoding="utf-8")
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        result = list_events_read_through(session, "bad-jsonl", run_dir)

        assert result.source == "artifact"
        assert result.items == []
        assert "events.jsonl" in result.warnings[0]


def test_alert_read_through_uses_artifact_shape(tmp_path):
    run_dir = _write_tiny_run(tmp_path)
    SessionLocal = _session_factory()

    with SessionLocal() as session:
        result = list_alerts_read_through(session, "run-compat", run_dir)

        assert result.source == "artifact"
        assert result.items[0]["alert_id"] == "alert-1"
