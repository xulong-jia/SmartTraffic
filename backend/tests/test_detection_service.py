from pathlib import Path

import cv2
import numpy as np

from app.services.detection_service import DetectionRunParams, DetectionService


def test_detection_service_runs_dry_run_pipeline_and_writes_artifacts(tmp_path: Path) -> None:
    video_path = tmp_path / "road.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for _ in range(5):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    service = DetectionService(results_dir=tmp_path / "traffic_analysis")
    result = service.run_detection(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage2",
        params=DetectionRunParams(dry_run=True, frame_stride=2, max_frames=2),
    )

    assert result["run_id"] == "run_stage2"
    assert result["video_id"] == "video_001"
    assert result["status"] == "completed"
    assert result["stage"] == "stage_2_yolov8_detection"
    assert result["next_stage"] == "stage_3_deepsort_tracking_not_started"
    assert result["total_frames_processed"] == 2
    assert result["total_detections"] == 0

    run_dir = tmp_path / "traffic_analysis" / "run_stage2"
    assert (run_dir / "metadata.json").is_file()
    assert (run_dir / "detections.csv").is_file()
    assert (run_dir / "detections.jsonl").is_file()
    assert (run_dir / "detection_summary.json").is_file()
