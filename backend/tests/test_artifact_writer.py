import csv
import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter


TRAJECTORY_FIELDNAMES = [
    "run_id",
    "video_id",
    "frame_index",
    "timestamp_ms",
    "track_id",
    "class_id",
    "class_name",
    "confidence",
    "state",
    "x1",
    "y1",
    "x2",
    "y2",
    "center_x",
    "center_y",
    "bottom_center_x",
    "bottom_center_y",
    "speed_px_per_frame",
    "speed_px_per_second",
    "direction_x",
    "direction_y",
    "moving_angle",
    "dwell_time_ms",
    "zone_ids_json",
    "zone_history_json",
    "lane_relation_json",
    "line_crossings_json",
    "track_length",
    "last_seen_frame",
    "last_seen_timestamp_ms",
]


def test_artifact_writer_creates_run_directory_and_metadata(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)

    run_dir = writer.create_run_directory(
        run_id="run_001",
        metadata={
            "video_id": "video_001",
            "detector_config": {"confidence_threshold": 0.25},
        },
    )

    metadata_path = run_dir / "metadata.json"
    assert run_dir == tmp_path / "run_001"
    assert metadata_path.is_file()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run_001"
    assert metadata["video_id"] == "video_001"
    assert metadata["artifacts"]["detections"] == "detections.csv"
    assert (run_dir / "keyframes").is_dir()


def test_artifact_writer_writes_stage_two_detection_outputs(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})
    frame_results = [
        {
            "frame_index": 0,
            "timestamp_ms": 0,
            "detections": [
                {
                    "class_id": 2,
                    "class_name": "car",
                    "confidence": 0.9,
                    "bbox": [1, 2, 30, 40],
                }
            ],
        },
        {"frame_index": 2, "timestamp_ms": 200, "detections": []},
    ]

    artifacts = writer.write_detection_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=frame_results,
    )

    assert artifacts["detections_csv"].name == "detections.csv"
    assert artifacts["detections_jsonl"].name == "detections.jsonl"
    assert artifacts["detection_summary"].name == "detection_summary.json"

    csv_text = artifacts["detections_csv"].read_text(encoding="utf-8")
    assert "run_id,video_id,frame_index,timestamp_ms,class_id,class_name" in csv_text
    assert "run_001,video_001,0,0,2,car,0.9,1.0,2.0,30.0,40.0" in csv_text

    jsonl_lines = artifacts["detections_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 2

    summary = json.loads(artifacts["detection_summary"].read_text(encoding="utf-8"))
    assert summary == {
        "total_frames_processed": 2,
        "total_detections": 1,
        "per_class_counts": {"car": 1},
    }


def test_write_trajectory_points_csv(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    artifacts = writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    assert artifacts["trajectory_points_csv"].name == "trajectory_points.csv"
    with artifacts["trajectory_points_csv"].open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert reader.fieldnames == TRAJECTORY_FIELDNAMES
    assert len(rows) == 3
    assert rows[0]["run_id"] == "run_001"
    assert rows[0]["video_id"] == "video_001"
    assert rows[0]["frame_index"] == "0"
    assert rows[0]["timestamp_ms"] == ""
    assert rows[0]["track_id"] == "1"
    assert rows[0]["x1"] == "10.0"
    assert rows[0]["y1"] == "10.0"
    assert rows[0]["x2"] == "24.0"
    assert rows[0]["y2"] == "24.0"
    assert rows[0]["center_x"] == "17.0"
    assert rows[0]["center_y"] == "17.0"
    assert rows[0]["bottom_center_x"] == "17.0"
    assert rows[0]["bottom_center_y"] == "24.0"
    assert rows[0]["direction_x"] == ""
    assert rows[0]["direction_y"] == ""


def test_write_trajectory_points_jsonl(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    artifacts = writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    assert artifacts["trajectory_points_jsonl"].name == "trajectory_points.jsonl"
    lines = artifacts["trajectory_points_jsonl"].read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in lines]

    assert len(payloads) == 3
    assert payloads[0]["run_id"] == "run_001"
    assert payloads[0]["video_id"] == "video_001"
    assert payloads[0]["frame_index"] == 0
    assert payloads[0]["timestamp_ms"] is None
    assert payloads[0]["trajectory_points"] == _trajectory_frames()[0][
        "trajectory_points"
    ]
    assert payloads[2] == {
        "run_id": "run_001",
        "video_id": "video_001",
        "frame_index": 2,
        "timestamp_ms": 200,
        "trajectory_points": [],
    }


def test_write_trajectory_summary(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    artifacts = writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    assert artifacts["trajectory_summary"].name == "trajectory_summary.json"
    summary = json.loads(artifacts["trajectory_summary"].read_text(encoding="utf-8"))
    assert summary == {
        "run_id": "run_001",
        "video_id": "video_001",
        "total_frames_processed": 3,
        "total_trajectory_points": 3,
        "unique_track_ids": 2,
        "per_class_track_counts": {"car": 1, "person": 1},
        "track_state_counts": {"confirmed": 2, "lost": 1},
        "avg_track_length": 1.5,
        "max_track_length": 2,
        "speed_unit": "px_per_second",
        "avg_speed_px_per_second": 5.0,
        "zone_counts": {"zone_a": 1, "zone_b": 1},
        "line_crossing_counts": {"line_1": 1},
    }


def test_artifact_writer_updates_metadata_with_trajectory_artifacts(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(
        run_id="run_001",
        metadata={
            "video_id": "video_001",
            "stage": "stage_3_deepsort_tracking",
            "detector_config": {"dry_run": True},
            "tracker_config": {"dry_run": True},
            "artifacts": {
                "detections_csv": "detections.csv",
                "tracks_csv": "tracks.csv",
            },
        },
    )

    writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    metadata = writer.read_metadata("run_001")
    assert metadata["stage"] == "stage_3_deepsort_tracking"
    assert metadata["detector_config"] == {"dry_run": True}
    assert metadata["tracker_config"] == {"dry_run": True}
    assert metadata["artifacts"]["detections_csv"] == "detections.csv"
    assert metadata["artifacts"]["tracks_csv"] == "tracks.csv"
    assert metadata["artifacts"]["trajectory_points"] == "trajectory_points.csv"
    assert metadata["artifacts"]["trajectory_points_csv"] == "trajectory_points.csv"
    assert metadata["artifacts"]["trajectory_points_jsonl"] == "trajectory_points.jsonl"
    assert metadata["artifacts"]["trajectory_summary"] == "trajectory_summary.json"


def test_trajectory_csv_serializes_json_fields(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    artifacts = writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    with artifacts["trajectory_points_csv"].open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert rows[1]["zone_ids_json"] == '["zone_b", "zone_a"]'
    assert rows[1]["zone_history_json"] == (
        '[{"entered_at": 100, "zone_id": "zone_b"}]'
    )
    assert rows[1]["lane_relation_json"] == (
        '{"confidence": 0.9, "lane_id": "lane_1"}'
    )
    assert rows[1]["line_crossings_json"] == (
        '[{"direction": "positive", "line_id": "line_1"}]'
    )


def test_trajectory_summary_counts_unique_tracks_and_states(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    artifacts = writer.write_trajectory_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=_trajectory_frames(),
    )

    summary = json.loads(artifacts["trajectory_summary"].read_text(encoding="utf-8"))
    assert summary["unique_track_ids"] == 2
    assert summary["per_class_track_counts"] == {"car": 1, "person": 1}
    assert summary["track_state_counts"] == {"confirmed": 2, "lost": 1}


def test_existing_detection_and_tracking_artifacts_still_work(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)
    writer.create_run_directory(run_id="run_001", metadata={"video_id": "video_001"})

    detection_artifacts = writer.write_detection_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.9,
                        "bbox": [1, 2, 30, 40],
                    }
                ],
            }
        ],
    )
    tracking_artifacts = writer.write_tracking_outputs(
        run_id="run_001",
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 0,
                "timestamp_ms": 0,
                "tracks": [
                    {
                        "track_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.9,
                        "bbox": [1, 2, 30, 40],
                        "center": [15.5, 21.0],
                        "state": "confirmed",
                    }
                ],
            }
        ],
    )

    assert detection_artifacts["detections_csv"].is_file()
    assert detection_artifacts["detections_jsonl"].is_file()
    assert detection_artifacts["detection_summary"].is_file()
    assert tracking_artifacts["tracks_csv"].is_file()
    assert tracking_artifacts["tracks_jsonl"].is_file()
    assert tracking_artifacts["tracking_summary"].is_file()


def _trajectory_frames() -> list[dict]:
    return [
        {
            "frame_index": 0,
            "timestamp_ms": None,
            "trajectory_points": [
                {
                    "track_id": 1,
                    "class_id": 2,
                    "class_name": "car",
                    "confidence": 0.91,
                    "bbox": [10.0, 10.0, 24.0, 24.0],
                    "center": [17.0, 17.0],
                    "bottom_center": [17.0, 24.0],
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
                    "last_seen_timestamp_ms": None,
                }
            ],
        },
        {
            "frame_index": 1,
            "timestamp_ms": 100,
            "trajectory_points": [
                {
                    "track_id": 1,
                    "class_id": 2,
                    "class_name": "car",
                    "confidence": 0.92,
                    "bbox": [11.0, 10.0, 25.0, 24.0],
                    "center": [18.0, 17.0],
                    "bottom_center": [18.0, 24.0],
                    "state": "confirmed",
                    "speed_px_per_frame": 1.0,
                    "speed_px_per_second": 10.0,
                    "direction_vector": [1.0, 0.0],
                    "moving_angle": 0.0,
                    "dwell_time_ms": 0,
                    "zone_ids": ["zone_b", "zone_a"],
                    "zone_history": [{"zone_id": "zone_b", "entered_at": 100}],
                    "lane_relation": {"lane_id": "lane_1", "confidence": 0.9},
                    "line_crossings": [
                        {"line_id": "line_1", "direction": "positive"}
                    ],
                    "track_length": 2,
                    "last_seen_frame": 1,
                    "last_seen_timestamp_ms": 100,
                },
                {
                    "track_id": 2,
                    "class_id": 0,
                    "class_name": "person",
                    "confidence": 0.81,
                    "bbox": [100.0, 50.0, 110.0, 80.0],
                    "center": [105.0, 65.0],
                    "bottom_center": [105.0, 80.0],
                    "state": "lost",
                    "speed_px_per_frame": 0.0,
                    "speed_px_per_second": 0.0,
                    "direction_vector": [0.0, 0.0],
                    "moving_angle": None,
                    "dwell_time_ms": 100,
                    "zone_ids": [],
                    "zone_history": [],
                    "lane_relation": {},
                    "line_crossings": [],
                    "track_length": 1,
                    "last_seen_frame": 1,
                    "last_seen_timestamp_ms": 100,
                },
            ],
        },
        {
            "frame_index": 2,
            "timestamp_ms": 200,
            "trajectory_points": [],
        },
    ]
