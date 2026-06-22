from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.services.tracking_service import TrackingRunParams, TrackingService


class MovingCarDetector:
    def detect_frame(
        self,
        frame: Any,
        frame_index: int,
        timestamp_ms: int | None = None,
    ) -> dict[str, Any]:
        x1 = 10.0 + float(frame_index)
        return {
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "detections": [
                {
                    "class_name": "car",
                    "class_id": 2,
                    "confidence": 0.9,
                    "bbox": [x1, 10.0, x1 + 12.0, 24.0],
                }
            ],
        }


def test_tracking_service_runs_dry_run_pipeline_and_writes_artifacts(tmp_path: Path) -> None:
    video_path = tmp_path / "road.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for _ in range(4):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    service = TrackingService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )
    result = service.run_tracking(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage3",
        params=TrackingRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            frame_stride=1,
            max_frames=3,
        ),
    )

    assert result["run_id"] == "run_stage3"
    assert result["video_id"] == "video_001"
    assert result["status"] == "completed"
    assert result["stage"] == "stage_3_deepsort_tracking"
    assert result["next_stage"] == "stage_4_trajectory_engine_not_started"
    assert result["total_frames_processed"] == 3
    assert result["total_detections"] == 3
    assert result["total_tracks"] == 3
    assert result["unique_track_ids"] == 1

    run_dir = tmp_path / "traffic_analysis" / "run_stage3"
    assert (run_dir / "metadata.json").is_file()
    assert (run_dir / "detections.csv").is_file()
    assert (run_dir / "detections.jsonl").is_file()
    assert (run_dir / "detection_summary.json").is_file()
    assert (run_dir / "tracks.csv").is_file()
    assert (run_dir / "tracks.jsonl").is_file()
    assert (run_dir / "tracking_summary.json").is_file()
