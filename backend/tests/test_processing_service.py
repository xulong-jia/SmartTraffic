from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_process_pipeline_runs_event_rules_and_generates_alerts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "app.services.processing_service.TrajectoryService",
        _FakeTrajectoryService,
    )
    _FakeTrajectoryService.last_params = None
    video_id = _upload_video(client, tmp_path)

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "mode": "detection_tracking_trajectory",
            "event_rules": [
                {
                    "rule_id": "rule_danger_001",
                    "name": "Danger zone",
                    "event_type": "danger_zone_intrusion",
                    "enabled": True,
                    "severity": "high",
                    "target_classes": ["car"],
                    "zone_id": "zone_001",
                    "parameters": {"point_type": "bottom_center"},
                    "cooldown_seconds": 0,
                    "min_track_length": 1,
                }
            ],
            "zones": [
                {
                    "zone_id": "zone_001",
                    "name": "Work zone",
                    "zone_type": "danger_zone",
                    "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                    "enabled": True,
                }
            ],
        },
    )

    assert process_response.status_code == 200
    process_payload = process_response.json()
    assert process_payload["status"] == "completed"
    assert process_payload["artifacts"]["events"] == "events.jsonl"
    assert process_payload["artifacts"]["alerts"] == "alerts.jsonl"
    assert _FakeTrajectoryService.last_params.config_snapshot["source"] == {
        "zones": "request",
        "rules": "request",
    }

    run_id = process_payload["run_id"]
    events_response = client.get(f"/api/analysis-runs/{run_id}/events")
    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert events_payload["summary"]["total_events"] == 1
    assert events_payload["events"][0]["event_type"] == "danger_zone_intrusion"
    assert events_payload["events"][0]["track_id"] == 7
    assert events_payload["event_evidence"][0]["evidence_type"] == "zone"
    assert events_payload["rule_executions"][0]["status"] == "matched"

    alerts_response = client.get(f"/api/analysis-runs/{run_id}/alerts")
    assert alerts_response.status_code == 200
    alerts_payload = alerts_response.json()
    assert alerts_payload["summary"]["total_alerts"] == 1
    assert alerts_payload["alerts"][0]["event_type"] == "danger_zone_intrusion"
    assert alerts_payload["alerts"][0]["level"] == "critical"
    assert alerts_payload["alerts"][0]["status"] == "new"


def test_process_pipeline_uses_db_config_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "app.services.processing_service.TrajectoryService",
        _FakeTrajectoryService,
    )
    _FakeTrajectoryService.last_params = None
    video_id = _upload_video(client, tmp_path)

    zone_response = client.post(
        "/api/zones",
        json={
            "id": "zone_db_danger",
            "name": "DB danger zone",
            "zone_type": "danger_zone",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "enabled": True,
            "video_id": video_id,
        },
    )
    assert zone_response.status_code == 201
    rule_response = client.post(
        "/api/event-rules",
        json={
            "id": "rule_db_danger",
            "name": "DB danger intrusion",
            "event_type": "danger_zone_intrusion",
            "zone_id": "zone_db_danger",
            "enabled": True,
            "severity": "high",
            "target_classes": ["car"],
        },
    )
    assert rule_response.status_code == 201

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={"mode": "detection_tracking_trajectory"},
    )

    assert process_response.status_code == 200
    process_payload = process_response.json()
    events_response = client.get(
        f"/api/analysis-runs/{process_payload['run_id']}/events"
    )
    assert events_response.status_code == 200
    assert events_response.json()["summary"]["total_events"] == 1
    assert _FakeTrajectoryService.last_params.zones[0]["zone_id"] == "zone_db_danger"
    assert _FakeTrajectoryService.last_params.config_snapshot["source"] == {
        "zones": "db",
        "rules": "db",
    }
    assert _FakeTrajectoryService.last_params.config_snapshot["event_rules"][0][
        "rule_id"
    ] == "rule_db_danger"


def test_process_pipeline_without_config_keeps_empty_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_run(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "app.services.processing_service.TrajectoryService",
        _FakeTrajectoryService,
    )
    _FakeTrajectoryService.last_params = None
    video_id = _upload_video(client, tmp_path)

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={"mode": "detection_tracking_trajectory"},
    )

    assert process_response.status_code == 200
    run_id = process_response.json()["run_id"]
    events_response = client.get(f"/api/analysis-runs/{run_id}/events")
    assert events_response.status_code == 200
    assert events_response.json()["summary"]["total_events"] == 0
    assert _FakeTrajectoryService.last_params.zones == []
    assert _FakeTrajectoryService.last_params.config_snapshot["source"] == {
        "zones": "db",
        "rules": "db",
    }


class _FakeTrajectoryService:
    last_params: Any = None

    def __init__(self, results_dir: str | Path | None = None, **_: Any) -> None:
        self.results_dir = Path(results_dir) if results_dir is not None else None

    def run_trajectory(
        self,
        *,
        video_id: str,
        video_path: str | Path,
        run_id: str | None = None,
        params: Any = None,
    ) -> dict[str, Any]:
        type(self).last_params = params
        effective_run_id = run_id or "run_fake_stage4"
        writer = TrafficArtifactWriter(self.results_dir or Path(video_path).parent)
        writer.create_run_directory(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "stage": "stage_4_trajectory_engine",
                "next_stage": "stage_5_event_engine_not_started",
                "processing_config_snapshot": getattr(params, "config_snapshot", None),
                "artifacts": {
                    "detections_csv": "detections.csv",
                    "detections_jsonl": "detections.jsonl",
                    "detection_summary": "detection_summary.json",
                    "tracks_csv": "tracks.csv",
                    "tracks_jsonl": "tracks.jsonl",
                    "tracking_summary": "tracking_summary.json",
                    "trajectory_points": "trajectory_points.csv",
                    "trajectory_points_csv": "trajectory_points.csv",
                    "trajectory_points_jsonl": "trajectory_points.jsonl",
                    "trajectory_summary": "trajectory_summary.json",
                },
            },
        )
        detection_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [40, 30, 60, 60],
                    }
                ],
            }
        ]
        tracking_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "tracks": [
                    {
                        "track_id": 7,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [40, 30, 60, 60],
                        "center": [50, 45],
                        "state": "confirmed",
                    }
                ],
            }
        ]
        trajectory_frames = [
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "trajectory_points": [
                    {
                        "track_id": 7,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.95,
                        "bbox": [40, 30, 60, 60],
                        "center": [50, 45],
                        "bottom_center": [50, 60],
                        "state": "confirmed",
                        "speed_px_per_frame": 0.0,
                        "speed_px_per_second": None,
                        "direction_vector": None,
                        "moving_angle": None,
                        "dwell_time_ms": 0,
                        "zone_ids": [],
                        "zone_history": [],
                        "lane_relation": {},
                        "line_crossings": [],
                        "track_length": 1,
                        "last_seen_frame": 0,
                        "last_seen_timestamp_ms": 0,
                    }
                ],
            }
        ]
        detection_artifacts = writer.write_detection_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=detection_frames,
        )
        tracking_artifacts = writer.write_tracking_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=tracking_frames,
        )
        trajectory_artifacts = writer.write_trajectory_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=trajectory_frames,
        )
        metadata = writer.read_metadata(effective_run_id)
        return {
            "run_id": effective_run_id,
            "video_id": video_id,
            "status": "completed",
            "stage": "stage_4_trajectory_engine",
            "next_stage": "stage_5_event_engine_not_started",
            "total_frames_processed": 1,
            "total_detections": 1,
            "total_tracks": 1,
            "unique_track_ids": 1,
            "total_trajectory_points": 1,
            "per_class_counts": {"car": 1},
            "per_class_track_counts": {"car": 1},
            "track_state_counts": {"confirmed": 1},
            "trajectory_track_state_counts": {"confirmed": 1},
            "avg_track_length": 1.0,
            "max_track_length": 1,
            "avg_speed_px_per_second": None,
            "result_dir": str((self.results_dir or Path(video_path).parent) / effective_run_id),
            "processing_config_snapshot": getattr(params, "config_snapshot", None),
            "artifacts": {
                **metadata["artifacts"],
                "detection_summary": detection_artifacts["detection_summary"].name,
                "tracking_summary": tracking_artifacts["tracking_summary"].name,
                "trajectory_summary": trajectory_artifacts["trajectory_summary"].name,
            },
        }


def _client_for_tmp_run(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _upload_video(client: TestClient, tmp_path: Path) -> str:
    video_path = _make_video(tmp_path / "upload.mp4", frame_count=2)
    with video_path.open("rb") as file:
        response = client.post(
            "/api/videos/upload",
            files={"file": ("upload.mp4", file, "video/mp4")},
        )
    assert response.status_code == 200
    return response.json()["id"]


def _make_video(path: Path, frame_count: int) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for index in range(frame_count):
        writer.write(np.full((48, 64, 3), index, dtype=np.uint8))
    writer.release()
    return path
