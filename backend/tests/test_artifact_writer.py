import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter


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
