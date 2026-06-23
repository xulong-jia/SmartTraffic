import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.alert_service import AlertService


def test_alert_service_writes_empty_outputs_for_empty_events(tmp_path: Path) -> None:
    run_id = _create_event_artifact_run(tmp_path, events=[])
    service = AlertService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.generate_alerts(run_id=run_id)

    run_dir = tmp_path / run_id
    assert result["status"] == "completed"
    assert result["total_alerts"] == 0
    assert result["alert_summary"]["total_alerts"] == 0
    assert _read_jsonl(run_dir / "alerts.jsonl") == []
    assert json.loads((run_dir / "alert_summary.json").read_text()) == {
        "run_id": run_id,
        "video_id": "video_001",
        "total_alerts": 0,
        "per_alert_type_counts": {},
        "per_level_counts": {},
        "per_status_counts": {},
        "unique_event_ids": 0,
        "unique_track_ids": 0,
        "first_alert_time_ms": None,
        "last_alert_time_ms": None,
    }


def test_alert_service_generates_alerts_from_events(tmp_path: Path) -> None:
    run_id = _create_event_artifact_run(
        tmp_path,
        events=[
            _event(event_id="event_high", event_type="danger_zone_intrusion", severity="high"),
            _event(event_id="event_medium", event_type="illegal_parking", severity="medium"),
            _event(event_id="event_low", event_type="pedestrian_in_vehicle_lane", severity="low"),
        ],
    )
    service = AlertService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.generate_alerts(run_id=run_id)

    alerts = _read_jsonl(tmp_path / run_id / "alerts.jsonl")
    assert result["total_alerts"] == 3
    assert [alert["level"] for alert in alerts] == ["critical", "warning", "info"]
    assert [alert["status"] for alert in alerts] == ["new", "new", "new"]
    assert alerts[0]["event_id"] == "event_high"
    assert alerts[0]["alert_type"] == "danger_zone_intrusion"


def test_alert_service_summary_and_metadata_merge(tmp_path: Path) -> None:
    run_id = _create_event_artifact_run(
        tmp_path,
        events=[
            _event(
                event_id="event_high",
                event_type="danger_zone_intrusion",
                severity="high",
                track_id=7,
                timestamp_ms=1000,
            ),
            _event(
                event_id="event_medium",
                event_type="illegal_parking",
                severity="medium",
                track_id=8,
                timestamp_ms=2000,
            ),
        ],
    )
    service = AlertService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.generate_alerts(run_id=run_id)

    summary = result["alert_summary"]
    assert summary["total_alerts"] == 2
    assert summary["per_alert_type_counts"] == {
        "danger_zone_intrusion": 1,
        "illegal_parking": 1,
    }
    assert summary["per_level_counts"] == {"critical": 1, "warning": 1}
    assert summary["per_status_counts"] == {"new": 2}
    assert summary["unique_event_ids"] == 2
    assert summary["unique_track_ids"] == 2
    assert summary["first_alert_time_ms"] == 1000
    assert summary["last_alert_time_ms"] == 2000

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    assert metadata["stage"] == "stage_4_trajectory_engine"
    assert metadata["artifacts"]["events"] == "events.jsonl"
    assert metadata["artifacts"]["event_summary"] == "event_summary.json"
    assert metadata["artifacts"]["alerts"] == "alerts.jsonl"
    assert metadata["artifacts"]["alerts_jsonl"] == "alerts.jsonl"
    assert metadata["artifacts"]["alert_summary"] == "alert_summary.json"
    assert "review" not in metadata["artifacts"]
    assert "evaluation" not in metadata["artifacts"]


def test_alert_service_missing_events_artifacts(tmp_path: Path) -> None:
    run_id = "run_without_events"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": run_id, "video_id": "video_001", "artifacts": {}}),
        encoding="utf-8",
    )
    service = AlertService(artifact_writer=TrafficArtifactWriter(tmp_path))

    with pytest.raises(FileNotFoundError, match="event artifacts not found"):
        service.generate_alerts(run_id=run_id)


def test_alert_service_skips_missing_event_id_and_deduplicates(tmp_path: Path) -> None:
    run_id = _create_event_artifact_run(
        tmp_path,
        events=[
            _event(event_id="event_duplicate", event_type="illegal_parking"),
            _event(event_id="event_duplicate", event_type="illegal_parking"),
            _event(event_id=None, event_type="danger_zone_intrusion"),
        ],
    )
    service = AlertService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.generate_alerts(run_id=run_id)

    alerts = _read_jsonl(tmp_path / run_id / "alerts.jsonl")
    assert result["total_alerts"] == 1
    assert len(alerts) == 1
    assert alerts[0]["event_id"] == "event_duplicate"


def _create_event_artifact_run(tmp_path: Path, events: list[dict]) -> str:
    run_id = "run_with_events"
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "stage": "stage_4_trajectory_engine",
            "artifacts": {
                "detections_csv": "detections.csv",
                "trajectory_summary": "trajectory_summary.json",
            },
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=events,
        event_evidence=[],
        rule_executions=[],
    )
    return run_id


def _event(
    *,
    event_id: str | None,
    event_type: str,
    severity: str | None = "medium",
    track_id: int | None = 7,
    timestamp_ms: int | None = 1000,
) -> dict:
    return {
        "event_id": event_id,
        "run_id": "run_with_events",
        "video_id": "video_001",
        "event_type": event_type,
        "severity": severity,
        "track_id": track_id,
        "class_name": "car",
        "zone_id": "zone_001",
        "rule_id": "rule_001",
        "start_frame": 10,
        "end_frame": 10,
        "start_time_ms": timestamp_ms,
        "end_time_ms": timestamp_ms,
        "confidence": 1.0,
        "status": "pending",
        "evidence": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
