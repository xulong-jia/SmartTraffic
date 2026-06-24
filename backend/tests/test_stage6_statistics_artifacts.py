import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.main import app
from app.services.processing_service import processing_service
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


def test_stage6_flow_counts_generated_from_flow_counting_events(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = _create_run_with_event_artifacts(
        writer,
        events=[
            _flow_counting_event(
                event_id="event_flow_1",
                track_id=17,
                class_name="car",
                zone_id="zone_entry",
                timestamp_ms=4_000,
            ),
            {
                "event_id": "event_wrong_way_1",
                "event_type": "wrong_way_driving",
                "track_id": 99,
                "class_name": "truck",
                "zone_id": "zone_entry",
                "end_time_ms": 4_200,
            },
        ],
        event_evidence=[
            _line_crossing_evidence(
                event_id="event_flow_1",
                track_id=17,
                class_name="car",
                zone_id="zone_entry",
                line_id="line_north",
                crossing_direction="positive",
                timestamp_ms=4_000,
            )
        ],
    )

    manifest = writer.write_statistics_outputs(run_id)

    payload = _read_json(tmp_path / run_id / "flow_counts.json")
    assert payload["schema_version"] == "stage6.flow_counts.v1"
    assert payload["summary"]["total_count"] == 1
    assert payload["summary"]["vehicle_count"] == 1
    assert payload["summary"]["person_count"] == 0
    assert payload["summary"]["by_class"] == {"car": 1}
    assert payload["summary"]["by_direction"] == {"in": 1}
    assert payload["summary"]["by_line"] == {"line_north": 1}
    assert payload["records"] == [
        {
            "event_id": "event_flow_1",
            "track_id": 17,
            "class_name": "car",
            "zone_id": "zone_entry",
            "counting_line_id": "line_north",
            "direction": "in",
            "frame_index": 12,
            "timestamp_ms": 4_000,
        }
    ]
    assert payload["windows"] == [
        {
            "time_window_start_ms": 0,
            "time_window_end_ms": 60_000,
            "zone_id": "zone_entry",
            "counting_line_id": "line_north",
            "class_name": "car",
            "direction": "in",
            "in_count": 1,
            "out_count": 0,
            "unknown_direction_count": 0,
            "total_count": 1,
            "track_ids": [17],
            "event_ids": ["event_flow_1"],
        }
    ]
    assert manifest["artifacts"]["flow_counts"]["status"] == "available"
    assert manifest["artifacts"]["flow_counts"]["record_count"] == 1
    assert manifest["artifacts"]["zone_statistics"]["status"] == "empty"


def test_stage6_statistics_artifacts_are_empty_without_source_records(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = _create_run_with_event_artifacts(
        writer,
        events=[
            {
                "event_id": "event_wrong_way_1",
                "event_type": "wrong_way_driving",
                "track_id": 99,
                "class_name": "truck",
                "zone_id": "zone_entry",
                "end_time_ms": 4_200,
            }
        ],
        event_evidence=[],
    )

    manifest = writer.write_statistics_outputs(run_id)

    flow_counts = _read_json(tmp_path / run_id / "flow_counts.json")
    zone_statistics = _read_json(tmp_path / run_id / "zone_statistics.json")
    assert flow_counts["summary"]["total_count"] == 0
    assert flow_counts["records"] == []
    assert flow_counts["windows"] == []
    assert zone_statistics["summary"]["total_windows"] == 0
    assert zone_statistics["congestion_events"] == []
    assert manifest["artifacts"]["flow_counts"]["status"] == "empty"
    assert manifest["artifacts"]["zone_statistics"]["status"] == "empty"


def test_stage6_zone_statistics_generated_from_congestion_evidence(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = _create_run_with_event_artifacts(
        writer,
        events=[
            {
                "event_id": "event_congestion_1",
                "event_type": "congestion",
                "track_id": None,
                "class_name": None,
                "zone_id": "zone_main",
                "end_frame": 22,
                "end_time_ms": 8_000,
            }
        ],
        event_evidence=[
            {
                "evidence_id": "evidence_zone_1",
                "event_id": "event_congestion_1",
                "event_type": "congestion",
                "evidence_type": "zone_statistics",
                "zone_id": "zone_main",
                "frame_index": 22,
                "timestamp_ms": 8_000,
                "evidence_json": {
                    "zone_id": "zone_main",
                    "vehicle_count": 6,
                    "avg_speed_px_per_frame": 1.2,
                    "track_ids": [1, 2, 3, 4, 5, 6],
                    "class_counts": {"car": 5, "truck": 1},
                },
            }
        ],
        trajectory_frames=[
            {
                "frame_index": 22,
                "timestamp_ms": 8_000,
                "trajectory_points": [
                    {
                        "track_id": 1,
                        "class_name": "car",
                        "speed_px_per_frame": 1.5,
                        "zone_ids": ["zone_main"],
                    },
                    {
                        "track_id": 7,
                        "class_name": "person",
                        "speed_px_per_frame": 0.8,
                        "zone_ids": ["zone_main"],
                    },
                ],
            }
        ],
    )

    manifest = writer.write_statistics_outputs(run_id)

    payload = _read_json(tmp_path / run_id / "zone_statistics.json")
    assert payload["schema_version"] == "stage6.zone_statistics.v1"
    assert payload["summary"]["zone_count"] == 1
    assert payload["summary"]["total_windows"] == 1
    assert payload["summary"]["max_vehicle_count"] == 6
    assert payload["summary"]["person_count"] == 1
    assert payload["summary"]["congestion_event_count"] == 1
    assert payload["windows"][0] == {
        "time_window_start_ms": 0,
        "time_window_end_ms": 60_000,
        "zone_id": "zone_main",
        "vehicle_count": 1,
        "person_count": 1,
        "occupancy_count": 2,
        "avg_speed_px_per_frame": 1.15,
        "class_counts": {"car": 1, "person": 1},
        "track_ids": [1, 7],
    }
    assert payload["congestion_events"] == [
        {
            "event_id": "event_congestion_1",
            "zone_id": "zone_main",
            "frame_index": 22,
            "timestamp_ms": 8_000,
            "vehicle_count": 6,
            "avg_speed_px_per_frame": 1.2,
            "track_ids": [1, 2, 3, 4, 5, 6],
            "class_counts": {"car": 5, "truck": 1},
        }
    ]
    assert manifest["artifacts"]["zone_statistics"]["status"] == "available"
    assert manifest["artifacts"]["zone_statistics"]["record_count"] == 2


def test_stage6_statistics_api_generates_and_returns_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)
    writer = TrafficArtifactWriter(tmp_path / "results")
    run_id = _create_run_with_event_artifacts(
        writer,
        events=[
            _flow_counting_event(
                event_id="event_flow_1",
                track_id=17,
                class_name="car",
                zone_id="zone_entry",
                timestamp_ms=4_000,
            )
        ],
        event_evidence=[
            _line_crossing_evidence(
                event_id="event_flow_1",
                track_id=17,
                class_name="car",
                zone_id="zone_entry",
                line_id="line_north",
                crossing_direction="positive",
                timestamp_ms=4_000,
            )
        ],
    )

    flow_response = client.get(f"/api/analysis-runs/{run_id}/flow-counts")
    zone_response = client.get(f"/api/analysis-runs/{run_id}/zone-statistics")

    assert flow_response.status_code == 200
    assert zone_response.status_code == 200
    assert flow_response.json()["summary"]["total_count"] == 1
    assert zone_response.json()["summary"]["total_windows"] == 0
    assert (tmp_path / "results" / run_id / "flow_counts.json").is_file()
    assert (tmp_path / "results" / run_id / "zone_statistics.json").is_file()


def test_stage6_statistics_api_missing_run_returns_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_for_tmp_results(tmp_path, monkeypatch)

    assert client.get("/api/analysis-runs/missing_run/flow-counts").status_code == 404
    assert (
        client.get("/api/analysis-runs/missing_run/zone-statistics").status_code
        == 404
    )


def _client_for_tmp_results(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("YOLO_DRY_RUN", "true")
    monkeypatch.setenv("DEEPSORT_DRY_RUN", "true")
    video_registry.clear()
    processing_service.clear()
    traffic_analysis_service.clear()
    return TestClient(app)


def _create_run_with_event_artifacts(
    writer: TrafficArtifactWriter,
    *,
    events: list[dict],
    event_evidence: list[dict],
    trajectory_frames: list[dict] | None = None,
) -> str:
    run_id = "run_stage6c"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "mode": "offline",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:01:00+00:00",
        },
    )
    writer.write_trajectory_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=trajectory_frames
        or [
            {
                "frame_index": 12,
                "timestamp_ms": 4_000,
                "trajectory_points": [
                    {
                        "track_id": 17,
                        "class_name": "car",
                        "speed_px_per_frame": 4.5,
                    }
                ],
            }
        ],
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=events,
        event_evidence=event_evidence,
        rule_executions=[],
    )
    return run_id


def _flow_counting_event(
    *,
    event_id: str,
    track_id: int,
    class_name: str,
    zone_id: str,
    timestamp_ms: int,
) -> dict:
    return {
        "event_id": event_id,
        "event_type": "flow_counting",
        "track_id": track_id,
        "class_name": class_name,
        "zone_id": zone_id,
        "end_frame": 12,
        "end_time_ms": timestamp_ms,
    }


def _line_crossing_evidence(
    *,
    event_id: str,
    track_id: int,
    class_name: str,
    zone_id: str,
    line_id: str,
    crossing_direction: str,
    timestamp_ms: int,
) -> dict:
    return {
        "evidence_id": f"evidence_{event_id}",
        "event_id": event_id,
        "event_type": "flow_counting",
        "evidence_type": "line_crossing",
        "track_id": track_id,
        "zone_id": zone_id,
        "frame_index": 12,
        "timestamp_ms": timestamp_ms,
        "evidence_json": {
            "line_id": line_id,
            "crossing_direction": crossing_direction,
            "track_id": track_id,
            "class_name": class_name,
            "frame_index": 12,
            "timestamp_ms": timestamp_ms,
        },
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
