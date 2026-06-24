import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.event_service import EventRunParams, EventService


def test_event_service_writes_empty_outputs_for_empty_rules(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    service = EventService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.run_events(
        run_id=run_id,
        params=EventRunParams(rules=[], zones=[]),
    )

    run_dir = tmp_path / run_id
    assert result["status"] == "completed"
    assert result["total_events"] == 0
    assert result["event_summary"]["total_events"] == 0
    assert _read_jsonl(run_dir / "events.jsonl") == []
    assert _read_jsonl(run_dir / "event_evidence.jsonl") == []
    assert _read_jsonl(run_dir / "rule_executions.jsonl") == []
    assert json.loads((run_dir / "event_summary.json").read_text())["total_events"] == 0
    assert json.loads((run_dir / "flow_counts.json").read_text())["records"] == []
    assert json.loads((run_dir / "zone_statistics.json").read_text())["windows"] == []


def test_event_service_generates_events_with_rules_and_zones(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    service = EventService(artifact_writer=TrafficArtifactWriter(tmp_path))

    result = service.run_events(
        run_id=run_id,
        params=EventRunParams(
            rules=[_danger_zone_rule()],
            zones=[_danger_zone()],
            record_not_matched=True,
        ),
    )

    run_dir = tmp_path / run_id
    events = _read_jsonl(run_dir / "events.jsonl")
    evidence = _read_jsonl(run_dir / "event_evidence.jsonl")
    executions = _read_jsonl(run_dir / "rule_executions.jsonl")
    summary = json.loads((run_dir / "event_summary.json").read_text())

    assert result["total_events"] == 1
    assert result["event_summary"]["per_event_type_counts"] == {
        "danger_zone_intrusion": 1
    }
    assert events[0]["event_type"] == "danger_zone_intrusion"
    assert events[0]["track_id"] == 7
    assert evidence[0]["event_id"] == events[0]["event_id"]
    assert executions[0]["status"] == "matched"
    assert summary["total_events"] == 1


def test_event_service_metadata_keeps_existing_artifacts(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    service = EventService(artifact_writer=TrafficArtifactWriter(tmp_path))

    service.run_events(run_id=run_id, params=EventRunParams(rules=[], zones=[]))

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    assert metadata["stage"] == "stage_4_trajectory_engine"
    assert metadata["artifacts"]["detections_csv"] == "detections.csv"
    assert metadata["artifacts"]["tracks_csv"] == "tracks.csv"
    assert metadata["artifacts"]["trajectory_points_jsonl"] == "trajectory_points.jsonl"
    assert metadata["artifacts"]["events"] == "events.jsonl"
    assert metadata["artifacts"]["events_jsonl"] == "events.jsonl"
    assert metadata["artifacts"]["event_evidence_jsonl"] == "event_evidence.jsonl"
    assert metadata["artifacts"]["rule_executions_jsonl"] == "rule_executions.jsonl"
    assert metadata["artifacts"]["event_summary"] == "event_summary.json"
    assert "alerts_jsonl" not in metadata["artifacts"]


def test_event_service_missing_trajectory_artifacts(tmp_path: Path) -> None:
    run_id = "run_without_trajectory"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": "video_001",
                "artifacts": {"detections_csv": "detections.csv"},
            }
        ),
        encoding="utf-8",
    )
    service = EventService(artifact_writer=TrafficArtifactWriter(tmp_path))

    with pytest.raises(FileNotFoundError, match="trajectory artifacts not found"):
        service.run_events(run_id=run_id)


def _create_trajectory_artifact_run(tmp_path: Path, video_id: str) -> str:
    run_id = "run_with_trajectory"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "video_id": video_id,
        "stage": "stage_4_trajectory_engine",
        "artifacts": {
            "detections_csv": "detections.csv",
            "tracks_csv": "tracks.csv",
            "trajectory_points_jsonl": "trajectory_points.jsonl",
            "trajectory_summary": "trajectory_summary.json",
        },
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    frames = [
        {
            "run_id": run_id,
            "video_id": video_id,
            "frame_index": 10,
            "timestamp_ms": 1000,
            "trajectory_points": [
                {
                    "track_id": 7,
                    "class_name": "car",
                    "track_length": 3,
                    "bottom_center": [50, 50],
                    "bbox": [40, 20, 60, 50],
                }
            ],
        }
    ]
    (run_dir / "trajectory_points.jsonl").write_text(
        "".join(json.dumps(frame, ensure_ascii=False) + "\n" for frame in frames),
        encoding="utf-8",
    )
    (run_dir / "trajectory_summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "video_id": video_id,
                "total_frames_processed": 1,
                "total_trajectory_points": 1,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
