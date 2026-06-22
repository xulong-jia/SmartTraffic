import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter, build_event_summary


def test_write_event_outputs(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(
        "run_001",
        {
            "video_id": "video_001",
            "artifacts": {
                "detections_csv": "detections.csv",
                "trajectory_summary": "trajectory_summary.json",
            },
        },
    )

    events = [_event(event_id="event_001", track_id=7)]
    evidence = [_evidence(event_id="event_001", track_id=7)]
    executions = [_execution(event_id="event_001", track_id=7, status="matched")]

    paths = writer.write_event_outputs(
        run_id="run_001",
        video_id="video_001",
        events=events,
        event_evidence=evidence,
        rule_executions=executions,
    )

    assert paths["events_jsonl"] == tmp_path / "run_001" / "events.jsonl"
    assert paths["event_evidence_jsonl"] == tmp_path / "run_001" / "event_evidence.jsonl"
    assert paths["rule_executions_jsonl"] == tmp_path / "run_001" / "rule_executions.jsonl"
    assert paths["event_summary"] == tmp_path / "run_001" / "event_summary.json"
    assert _read_jsonl(paths["events_jsonl"]) == events
    assert _read_jsonl(paths["event_evidence_jsonl"]) == evidence
    assert _read_jsonl(paths["rule_executions_jsonl"]) == executions


def test_write_event_outputs_empty_events(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(tmp_path)

    paths = writer.write_event_outputs(
        run_id="run_empty",
        video_id="video_001",
        events=[],
        event_evidence=[],
        rule_executions=[],
    )

    assert _read_jsonl(paths["events_jsonl"]) == []
    assert _read_jsonl(paths["event_evidence_jsonl"]) == []
    assert _read_jsonl(paths["rule_executions_jsonl"]) == []
    summary = json.loads(paths["event_summary"].read_text(encoding="utf-8"))
    assert summary == {
        "run_id": "run_empty",
        "video_id": "video_001",
        "total_events": 0,
        "per_event_type_counts": {},
        "per_severity_counts": {},
        "per_status_counts": {},
        "unique_track_ids": 0,
        "rule_execution_counts": {},
        "first_event_time_ms": None,
        "last_event_time_ms": None,
    }


def test_build_event_summary_counts_events_and_rule_executions() -> None:
    summary = build_event_summary(
        events=[
            _event(
                event_id="event_001",
                event_type="danger_zone_intrusion",
                severity="high",
                status="pending",
                track_id=7,
                start_time_ms=1000,
                end_time_ms=1400,
            ),
            _event(
                event_id="event_002",
                event_type="illegal_parking",
                severity="medium",
                status="resolved",
                track_id=7,
                start_time_ms=2000,
                end_time_ms=2400,
            ),
            _event(
                event_id="event_003",
                event_type="illegal_parking",
                severity="medium",
                status="pending",
                track_id=None,
                start_time_ms=None,
                end_time_ms=None,
            ),
        ],
        rule_executions=[
            _execution(status="matched"),
            _execution(status="skipped"),
            _execution(status="error"),
        ],
        run_id="run_001",
        video_id="video_001",
    )

    assert summary["total_events"] == 3
    assert summary["per_event_type_counts"] == {
        "danger_zone_intrusion": 1,
        "illegal_parking": 2,
    }
    assert summary["per_severity_counts"] == {"high": 1, "medium": 2}
    assert summary["per_status_counts"] == {"pending": 2, "resolved": 1}
    assert summary["unique_track_ids"] == 1
    assert summary["rule_execution_counts"] == {
        "error": 1,
        "matched": 1,
        "skipped": 1,
    }
    assert summary["first_event_time_ms"] == 1000
    assert summary["last_event_time_ms"] == 2400


def test_write_event_outputs_merges_metadata_artifacts_without_overwriting_existing(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    writer.create_run_directory(
        "run_001",
        {
            "video_id": "video_001",
            "stage": "stage_4_trajectory_engine",
            "artifacts": {
                "detections_csv": "detections.csv",
                "tracks_csv": "tracks.csv",
                "trajectory_summary": "trajectory_summary.json",
            },
        },
    )

    writer.write_event_outputs(
        run_id="run_001",
        video_id="video_001",
        events=[],
        event_evidence=[],
        rule_executions=[],
    )

    metadata = json.loads((tmp_path / "run_001" / "metadata.json").read_text())
    assert metadata["stage"] == "stage_4_trajectory_engine"
    assert metadata["artifacts"]["detections_csv"] == "detections.csv"
    assert metadata["artifacts"]["tracks_csv"] == "tracks.csv"
    assert metadata["artifacts"]["trajectory_summary"] == "trajectory_summary.json"
    assert metadata["artifacts"]["events"] == "events.jsonl"
    assert metadata["artifacts"]["events_jsonl"] == "events.jsonl"
    assert metadata["artifacts"]["event_evidence_jsonl"] == "event_evidence.jsonl"
    assert metadata["artifacts"]["rule_executions_jsonl"] == "rule_executions.jsonl"
    assert metadata["artifacts"]["event_summary"] == "event_summary.json"
    assert "alerts_jsonl" not in metadata["artifacts"]


def _event(
    event_id: str = "event_001",
    event_type: str = "danger_zone_intrusion",
    severity: str = "high",
    status: str = "pending",
    track_id: int | None = 7,
    start_time_ms: int | None = 1000,
    end_time_ms: int | None = 1300,
) -> dict:
    return {
        "event_id": event_id,
        "run_id": "run_001",
        "video_id": "video_001",
        "event_type": event_type,
        "severity": severity,
        "track_id": track_id,
        "class_name": "car",
        "zone_id": "zone_001",
        "rule_id": "rule_001",
        "start_frame": 10,
        "end_frame": 13,
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "confidence": 1.0,
        "status": status,
        "evidence": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _evidence(event_id: str = "event_001", track_id: int | None = 7) -> dict:
    return {
        "evidence_id": "evidence_001",
        "event_id": event_id,
        "run_id": "run_001",
        "video_id": "video_001",
        "track_id": track_id,
        "frame_index": 10,
        "timestamp_ms": 1000,
        "evidence_type": "trajectory",
        "evidence_json": {},
        "snapshot_path": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _execution(
    event_id: str | None = "event_001",
    track_id: int | None = 7,
    status: str = "matched",
) -> dict:
    return {
        "execution_id": f"execution_{status}",
        "run_id": "run_001",
        "rule_id": "rule_001",
        "event_id": event_id,
        "track_id": track_id,
        "frame_index": 10,
        "status": status,
        "input_features": {},
        "output_result": {},
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
