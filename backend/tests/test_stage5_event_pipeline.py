import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.alert_service import AlertService
from app.services.event_service import EventRunParams, EventService


def test_stage5_pipeline_generates_event_and_alert_artifacts(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path)
    writer = TrafficArtifactWriter(tmp_path)

    event_result = EventService(artifact_writer=writer).run_events(
        run_id=run_id,
        params=EventRunParams(
            rules=[_danger_zone_rule()],
            zones=[_danger_zone()],
        ),
    )
    alert_result = AlertService(artifact_writer=writer).generate_alerts(run_id=run_id)

    run_dir = tmp_path / run_id
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    artifact_index = writer.artifact_index(run_id)
    events = _read_jsonl(run_dir / "events.jsonl")
    evidence = _read_jsonl(run_dir / "event_evidence.jsonl")
    executions = _read_jsonl(run_dir / "rule_executions.jsonl")
    alerts = _read_jsonl(run_dir / "alerts.jsonl")

    assert event_result["total_events"] == 1
    assert alert_result["total_alerts"] == 1
    assert events[0]["event_type"] == "danger_zone_intrusion"
    assert evidence[0]["event_id"] == events[0]["event_id"]
    assert executions[0]["event_id"] == events[0]["event_id"]
    assert alerts[0]["event_id"] == events[0]["event_id"]
    assert alerts[0]["level"] == "critical"
    assert alerts[0]["status"] == "new"
    assert alerts[0]["id"] == alerts[0]["alert_id"]
    assert "event_evidence_id" in alerts[0]
    assert "snapshot_path" in alerts[0]

    for artifact_name in [
        "events.jsonl",
        "event_evidence.jsonl",
        "rule_executions.jsonl",
        "alerts.jsonl",
    ]:
        assert (run_dir / artifact_name).is_file()

    assert metadata["alerts_count"] == 1
    assert artifact_index["alerts_jsonl"] == "alerts.jsonl"
    for relative_path in artifact_index.values():
        assert (run_dir / relative_path).exists(), relative_path


def test_alert_generation_deduplicates_same_track_zone_type_in_cooldown(
    tmp_path: Path,
) -> None:
    run_id = "run_with_duplicate_events"
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(run_id, {"video_id": "video_001"})
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            _event("event_1", timestamp_ms=1000),
            _event("event_2", timestamp_ms=1500),
            _event("event_3", timestamp_ms=90000),
        ],
        event_evidence=[],
        rule_executions=[],
    )

    result = AlertService(artifact_writer=writer).generate_alerts(run_id=run_id)

    alerts = _read_jsonl(tmp_path / run_id / "alerts.jsonl")
    assert result["total_alerts"] == 2
    assert [alert["event_id"] for alert in alerts] == ["event_1", "event_3"]


def _create_trajectory_artifact_run(tmp_path: Path) -> str:
    run_id = "run_stage5"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": "video_001",
                "artifacts": {
                    "trajectory_points_jsonl": "trajectory_points.jsonl",
                    "trajectory_summary": "trajectory_summary.json",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    frame = {
        "run_id": run_id,
        "video_id": "video_001",
        "frame_index": 10,
        "timestamp_ms": 1000,
        "trajectory_points": [
            {
                "track_id": 7,
                "class_name": "car",
                "track_length": 3,
                "bottom_center": [50, 50],
                "center": [50, 35],
                "bbox": [40, 20, 60, 50],
            }
        ],
    }
    (run_dir / "trajectory_points.jsonl").write_text(
        json.dumps(frame, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "trajectory_summary.json").write_text("{}\n", encoding="utf-8")
    return run_id


def _danger_zone_rule() -> dict:
    return {
        "rule_id": "rule_danger_zone_1",
        "name": "Danger Zone Intrusion",
        "event_type": "danger_zone_intrusion",
        "severity": "high",
        "zone_id": "danger_zone_1",
        "parameters": {},
        "cooldown_seconds": 0,
        "min_track_length": 1,
    }


def _danger_zone() -> dict:
    return {
        "zone_id": "danger_zone_1",
        "name": "Danger Zone",
        "zone_type": "danger_zone",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "enabled": True,
    }


def _event(event_id: str, *, timestamp_ms: int) -> dict:
    return {
        "event_id": event_id,
        "run_id": "run_with_duplicate_events",
        "video_id": "video_001",
        "event_type": "danger_zone_intrusion",
        "severity": "high",
        "track_id": 7,
        "class_name": "car",
        "zone_id": "danger_zone_1",
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
