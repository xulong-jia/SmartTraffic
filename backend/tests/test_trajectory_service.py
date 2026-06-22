import csv
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from app.services.trajectory_service import TrajectoryRunParams, TrajectoryService


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


class EmptyTracker:
    def update(
        self,
        frame: Any,
        detections: list[dict[str, Any]],
        frame_index: int,
        timestamp_ms: int | None = None,
    ) -> dict[str, Any]:
        return {"frame_index": frame_index, "timestamp_ms": timestamp_ms, "tracks": []}

    def get_tracker_info(self) -> dict[str, Any]:
        return {"dry_run": True, "available": True, "empty": True}


def test_trajectory_service_dry_run_pipeline(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=4)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            frame_stride=1,
            max_frames=3,
        ),
    )

    assert result["status"] == "completed"
    run_dir = tmp_path / "traffic_analysis" / "run_stage4"
    for artifact_name in [
        "detections.csv",
        "detections.jsonl",
        "detection_summary.json",
        "tracks.csv",
        "tracks.jsonl",
        "tracking_summary.json",
        "trajectory_points.csv",
        "trajectory_points.jsonl",
        "trajectory_summary.json",
    ]:
        assert (run_dir / artifact_name).is_file()


def test_trajectory_service_returns_stable_contract(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=4)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=3,
        ),
    )

    assert result["run_id"] == "run_stage4"
    assert result["video_id"] == "video_001"
    assert result["stage"] == "stage_4_trajectory_engine"
    assert result["next_stage"] == "stage_5_event_engine_not_started"
    assert result["total_frames_processed"] == 3
    assert result["total_detections"] == 3
    assert result["total_tracks"] == 3
    assert result["unique_track_ids"] == 1
    assert result["total_trajectory_points"] == 3
    assert result["per_class_counts"] == {"car": 3}
    assert result["per_class_track_counts"] == {"car": 1}
    assert result["track_state_counts"] == {"confirmed": 3}
    assert result["trajectory_track_state_counts"] == {"confirmed": 3}
    assert result["avg_track_length"] == pytest.approx(3.0)
    assert result["max_track_length"] == 3
    assert result["avg_speed_px_per_second"] is not None
    assert result["artifacts"] == {
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
    }


def test_trajectory_service_writes_metadata_stage_4(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=3)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )

    service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=2,
            direction_window=2,
            dwell_speed_threshold=1.0,
        ),
    )

    metadata = json.loads(
        (tmp_path / "traffic_analysis" / "run_stage4" / "metadata.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["stage"] == "stage_4_trajectory_engine"
    assert metadata["next_stage"] == "stage_5_event_engine_not_started"
    assert metadata["detector_config"]["dry_run"] is True
    assert metadata["tracker_config"]["dry_run"] is True
    assert metadata["trajectory_config"] == {
        "fps": pytest.approx(10.0),
        "direction_window": 2,
        "dwell_speed_threshold": 1.0,
        "max_history_points": None,
    }
    assert metadata["artifacts"]["detections_csv"] == "detections.csv"
    assert metadata["artifacts"]["tracks_csv"] == "tracks.csv"
    assert metadata["artifacts"]["trajectory_points_csv"] == "trajectory_points.csv"
    assert "alert" not in metadata
    assert "review" not in metadata
    assert "bad_case" not in metadata
    assert "evaluation" not in metadata
    assert "alerts" not in metadata["artifacts"]
    assert "evaluation_summary" not in metadata["artifacts"]


def test_trajectory_service_respects_max_frames(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=5)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=2,
        ),
    )

    assert result["total_frames_processed"] == 2


def test_trajectory_service_max_frames_zero_writes_empty_outputs(
    tmp_path: Path,
) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=3)
    service = TrajectoryService(results_dir=tmp_path / "traffic_analysis")

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=0,
        ),
    )

    assert result["status"] == "completed"
    assert result["total_frames_processed"] == 0
    assert result["total_detections"] == 0
    assert result["total_tracks"] == 0
    assert result["unique_track_ids"] == 0
    assert result["total_trajectory_points"] == 0
    run_dir = tmp_path / "traffic_analysis" / "run_stage4"
    assert (run_dir / "detections.csv").is_file()
    assert (run_dir / "tracks.csv").is_file()
    assert (run_dir / "trajectory_points.csv").is_file()
    assert (run_dir / "detections.jsonl").read_text(encoding="utf-8") == ""
    assert (run_dir / "tracks.jsonl").read_text(encoding="utf-8") == ""
    assert (run_dir / "trajectory_points.jsonl").read_text(encoding="utf-8") == ""


def test_trajectory_service_does_not_require_real_model(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=2)
    service = TrajectoryService(results_dir=tmp_path / "traffic_analysis")

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=1,
        ),
    )

    assert result["status"] == "completed"
    assert result["total_frames_processed"] == 1
    assert result["total_detections"] == 0


def test_trajectory_service_uses_trajectory_engine_outputs(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=4)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        results_dir=tmp_path / "traffic_analysis",
    )

    service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=3,
        ),
    )

    with (tmp_path / "traffic_analysis" / "run_stage4" / "trajectory_points.csv").open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert rows[-1]["track_length"] == "3"
    assert float(rows[-1]["speed_px_per_frame"]) > 0.0
    assert rows[-1]["moving_angle"] != ""


def test_trajectory_service_handles_empty_tracks(tmp_path: Path) -> None:
    video_path = _make_video(tmp_path / "road.mp4", frame_count=3)
    service = TrajectoryService(
        detector=MovingCarDetector(),
        tracker=EmptyTracker(),
        results_dir=tmp_path / "traffic_analysis",
    )

    result = service.run_trajectory(
        video_id="video_001",
        video_path=video_path,
        run_id="run_stage4",
        params=TrajectoryRunParams(
            detector_dry_run=True,
            tracker_dry_run=True,
            max_frames=2,
        ),
    )

    assert result["total_detections"] == 2
    assert result["total_tracks"] == 0
    assert result["total_trajectory_points"] == 0
    summary = json.loads(
        (
            tmp_path / "traffic_analysis" / "run_stage4" / "trajectory_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["total_frames_processed"] == 2
    assert summary["total_trajectory_points"] == 0


def _make_video(path: Path, frame_count: int) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for index in range(frame_count):
        frame = np.full((48, 64, 3), index, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path
