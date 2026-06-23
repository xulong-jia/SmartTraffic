import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.event_service import EventRunParams, EventService


def test_event_artifacts_metadata_counts_and_existing_artifact_index(
    tmp_path: Path,
) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path)

    result = EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
        params=EventRunParams(
            rules=[_danger_zone_rule()],
            zones=[_danger_zone()],
            record_not_matched=True,
        ),
    )

    run_dir = tmp_path / run_id
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    artifacts = metadata["artifacts"]
    events = _read_jsonl(run_dir / artifacts["events_jsonl"])
    evidence = _read_jsonl(run_dir / artifacts["event_evidence_jsonl"])
    executions = _read_jsonl(run_dir / artifacts["rule_executions_jsonl"])

    assert result["total_events"] == 1
    assert metadata["event_config_snapshot"]["source"] == {
        "rules": "request",
        "zones": "request",
    }
    assert metadata["enabled_rules_count"] == 1
    assert metadata["enabled_zones_count"] == 1
    assert metadata["events_count"] == len(events) == 1
    assert metadata["event_evidence_count"] == len(evidence) == 1
    assert metadata["rule_executions_count"] == len(executions) == 1
    assert metadata["alerts_count"] == 0

    assert "alerts_jsonl" not in artifacts
    assert "alert_summary" not in artifacts
    for relative_path in artifacts.values():
        assert (run_dir / relative_path).exists(), relative_path

    evidence_json = evidence[0]["evidence_json"]
    assert evidence[0]["event_id"] == events[0]["event_id"]
    assert evidence_json["rule_parameters"] == {}
    assert evidence_json["trigger_reason"] == "inside_danger_zone"
    assert evidence_json["snapshot_available"] is False


def test_event_artifacts_empty_events_have_zero_counts_and_real_files(
    tmp_path: Path,
) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path)

    EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
        params=EventRunParams(rules=[], zones=[]),
    )

    run_dir = tmp_path / run_id
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    artifacts = metadata["artifacts"]

    assert metadata["events_count"] == 0
    assert metadata["event_evidence_count"] == 0
    assert metadata["rule_executions_count"] == 0
    assert metadata["alerts_count"] == 0
    assert _read_jsonl(run_dir / artifacts["events_jsonl"]) == []
    assert _read_jsonl(run_dir / artifacts["event_evidence_jsonl"]) == []
    assert _read_jsonl(run_dir / artifacts["rule_executions_jsonl"]) == []
    for relative_path in artifacts.values():
        assert (run_dir / relative_path).exists(), relative_path


def _create_trajectory_artifact_run(tmp_path: Path) -> str:
    run_id = "run_with_trajectory"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "video_id": "video_001",
        "stage": "stage_4_trajectory_engine",
        "artifacts": {
            "trajectory_points_jsonl": "trajectory_points.jsonl",
            "trajectory_summary": "trajectory_summary.json",
        },
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
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
                "speed_px_per_frame": 1.0,
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


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
