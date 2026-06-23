import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.services.event_rule_service import event_rule_service
from app.services.event_service import EventRunParams, EventService
from app.services.zone_service import zone_service


@pytest.fixture(autouse=True)
def clear_config_services():
    zone_service.clear()
    event_rule_service.clear()
    yield
    zone_service.clear()
    event_rule_service.clear()


def test_event_service_reads_enabled_config_and_writes_snapshot(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    zone_service.create_zone(
        {
            "id": "danger_zone_1",
            "name": "Danger Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "enabled": True,
            "video_id": "video_001",
        }
    )
    event_rule_service.create_rule(
        {
            "id": "rule_danger_zone_1",
            "name": "Danger Zone Intrusion",
            "event_type": "danger_zone_intrusion",
            "zone_id": "danger_zone_1",
            "severity": "high",
            "enabled": True,
        }
    )

    result = EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
    )

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    snapshot = metadata["event_config_snapshot"]
    assert result["total_events"] == 1
    assert snapshot["source"] == {"rules": "service", "zones": "service"}
    assert snapshot["zones"][0]["zone_id"] == "danger_zone_1"
    assert snapshot["event_rules"][0]["rule_id"] == "rule_danger_zone_1"
    assert snapshot["event_rules"][0]["event_type"] == "danger_zone_intrusion"


def test_event_service_excludes_disabled_rules_from_default_config(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    zone_service.create_zone(
        {
            "id": "danger_zone_1",
            "name": "Danger Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "enabled": True,
            "video_id": "video_001",
        }
    )
    event_rule_service.create_rule(
        {
            "id": "rule_disabled",
            "name": "Disabled Danger Rule",
            "event_type": "danger_zone_intrusion",
            "zone_id": "danger_zone_1",
            "enabled": False,
        }
    )

    result = EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
    )

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    assert result["total_events"] == 0
    assert metadata["event_config_snapshot"]["event_rules"] == []


def test_event_service_request_config_overrides_stored_config(tmp_path: Path) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    event_rule_service.create_rule(
        {
            "id": "rule_stored",
            "name": "Stored Danger Rule",
            "event_type": "danger_zone_intrusion",
            "zone_id": "stored_zone",
            "enabled": True,
        }
    )

    result = EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
        params=EventRunParams(rules=[], zones=[]),
    )

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    assert result["total_events"] == 0
    assert metadata["event_config_snapshot"]["source"] == {
        "rules": "request",
        "zones": "request",
    }
    assert metadata["event_config_snapshot"]["event_rules"] == []


def test_event_service_default_config_filters_rules_by_video_zones(
    tmp_path: Path,
) -> None:
    run_id = _create_trajectory_artifact_run(tmp_path, video_id="video_001")
    zone_service.create_zone(
        {
            "id": "zone_video_001",
            "name": "Current Video Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "video_id": "video_001",
        }
    )
    zone_service.create_zone(
        {
            "id": "zone_other_video",
            "name": "Other Video Zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "video_id": "video_002",
        }
    )
    event_rule_service.create_rule(
        {
            "id": "rule_current_video",
            "name": "Current Video Rule",
            "event_type": "danger_zone_intrusion",
            "zone_id": "zone_video_001",
        }
    )
    event_rule_service.create_rule(
        {
            "id": "rule_other_video",
            "name": "Other Video Rule",
            "event_type": "danger_zone_intrusion",
            "zone_id": "zone_other_video",
        }
    )

    EventService(artifact_writer=TrafficArtifactWriter(tmp_path)).run_events(
        run_id=run_id,
    )

    metadata = json.loads((tmp_path / run_id / "metadata.json").read_text())
    snapshot = metadata["event_config_snapshot"]
    assert [zone["zone_id"] for zone in snapshot["zones"]] == ["zone_video_001"]
    assert [rule["rule_id"] for rule in snapshot["event_rules"]] == [
        "rule_current_video"
    ]


def _create_trajectory_artifact_run(tmp_path: Path, video_id: str) -> str:
    run_id = "run_with_trajectory"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "video_id": video_id,
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
    (run_dir / "trajectory_summary.json").write_text("{}\n", encoding="utf-8")
    return run_id
