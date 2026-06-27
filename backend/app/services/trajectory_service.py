from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings
from app.cv.deepsort_tracker import DeepSortTracker
from app.cv.frame_reader import iter_frames, read_video_metadata
from app.cv.yolo_detector import YoloDetector
from app.trajectory.engine import TrajectoryEngine


STAGE_4_ARTIFACTS = {
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


@dataclass(frozen=True)
class TrajectoryRunParams:
    model_path: str | None = None
    conf_threshold: float | None = None
    iou_threshold: float | None = None
    image_size: int | None = None
    device: str | None = None

    detector_dry_run: bool | None = None
    tracker_dry_run: bool | None = None
    frame_stride: int | None = None
    max_frames: int | None = None
    write_preview: bool | None = None

    deepsort_max_age: int | None = None
    deepsort_n_init: int | None = None
    deepsort_max_iou_distance: float | None = None
    deepsort_max_cosine_distance: float | None = None
    tracking_min_confidence: float | None = None
    tracking_target_classes: tuple[str, ...] | list[str] | set[str] | None = None

    fps: float | None = None
    direction_window: int = 2
    dwell_speed_threshold: float = 1.0
    max_history_points: int | None = None
    zones: list[dict[str, Any]] | None = None
    config_snapshot: dict[str, Any] | None = None


class TrajectoryService:
    """Stage-four offline trajectory pipeline orchestration."""

    def __init__(
        self,
        detector: Any | None = None,
        tracker: Any | None = None,
        trajectory_engine: TrajectoryEngine | None = None,
        artifact_writer: TrafficArtifactWriter | None = None,
        results_dir: str | Path | None = None,
    ) -> None:
        self.detector = detector
        self.tracker = tracker
        self.trajectory_engine = trajectory_engine
        self.artifact_writer = artifact_writer
        self.results_dir = Path(results_dir) if results_dir is not None else None

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_4_trajectory_engine"}

    def run_trajectory(
        self,
        *,
        video_id: str,
        video_path: str | Path,
        run_id: str | None = None,
        params: TrajectoryRunParams | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        effective_params = params or TrajectoryRunParams()
        effective_run_id = run_id or f"run_{uuid4().hex[:12]}"
        writer = self.artifact_writer or TrafficArtifactWriter(
            self.results_dir or settings.results_dir
        )
        metadata = read_video_metadata(video_path)
        started_at = _utc_now_iso()

        detector_config = _build_detector_config(effective_params, settings)
        tracker_config = _build_tracker_config(effective_params, settings)
        trajectory_config = _build_trajectory_config(effective_params, metadata)
        zones = [dict(zone) for zone in effective_params.zones or []]
        frame_stride = (
            effective_params.frame_stride
            if effective_params.frame_stride is not None
            else settings.video_frame_stride
        )
        max_frames = (
            effective_params.max_frames
            if effective_params.max_frames is not None
            else settings.detection_max_frames
        )
        _validate_frame_limits(frame_stride=frame_stride, max_frames=max_frames)

        run_dir = writer.create_run_directory(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "mode": "offline",
                "stage": "stage_4_trajectory_engine",
                "next_stage": "stage_5_event_engine_not_started",
                "detector_config": detector_config,
                "tracker_config": tracker_config,
                "trajectory_config": trajectory_config,
                "processing_config_snapshot": effective_params.config_snapshot,
                "started_at": started_at,
                "finished_at": "",
                "video_metadata": metadata,
                "artifacts": dict(STAGE_4_ARTIFACTS),
            },
        )

        detector = self.detector or YoloDetector(**detector_config)
        tracker = self.tracker or DeepSortTracker(**tracker_config)
        if self.tracker is not None and hasattr(tracker, "reset"):
            tracker.reset()
        trajectory_engine = self.trajectory_engine or TrajectoryEngine(
            **trajectory_config
        )
        if self.trajectory_engine is not None and hasattr(trajectory_engine, "reset"):
            trajectory_engine.reset()

        detection_frame_results: list[dict[str, Any]] = []
        tracking_frame_results: list[dict[str, Any]] = []
        trajectory_frame_results: list[dict[str, Any]] = []

        if max_frames != 0:
            for frame_item in iter_frames(
                video_path,
                frame_stride=frame_stride,
                max_frames=max_frames,
            ):
                frame_index = int(frame_item["frame_index"])
                timestamp_ms = int(frame_item["timestamp_ms"])
                detection_result = detector.detect_frame(
                    frame_item["frame"],
                    frame_index=frame_index,
                    timestamp_ms=timestamp_ms,
                )
                tracking_result = tracker.update(
                    frame_item["frame"],
                    detection_result.get("detections", []),
                    frame_index=frame_index,
                    timestamp_ms=timestamp_ms,
                )
                trajectory_result = trajectory_engine.update(tracking_result, zones=zones)
                detection_frame_results.append(detection_result)
                tracking_frame_results.append(tracking_result)
                trajectory_frame_results.append(trajectory_result)

        detection_artifacts = writer.write_detection_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=detection_frame_results,
        )
        tracking_artifacts = writer.write_tracking_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=tracking_frame_results,
        )
        trajectory_artifacts = writer.write_trajectory_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=trajectory_frame_results,
        )
        detection_summary = _read_json(detection_artifacts["detection_summary"])
        tracking_summary = _read_json(tracking_artifacts["tracking_summary"])
        trajectory_summary = _read_json(trajectory_artifacts["trajectory_summary"])
        finished_at = _utc_now_iso()
        artifacts = dict(STAGE_4_ARTIFACTS)

        writer.update_metadata(
            effective_run_id,
            {
                "run_id": effective_run_id,
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "mode": "offline",
                "stage": "stage_4_trajectory_engine",
                "next_stage": "stage_5_event_engine_not_started",
                "detector_config": detector.get_model_info()
                if hasattr(detector, "get_model_info")
                else detector_config,
                "tracker_config": tracker.get_tracker_info()
                if hasattr(tracker, "get_tracker_info")
                else tracker_config,
                "trajectory_config": trajectory_config,
                "processing_config_snapshot": effective_params.config_snapshot,
                "started_at": started_at,
                "finished_at": finished_at,
                "video_metadata": metadata,
                "artifacts": artifacts,
                "detection_summary": detection_summary,
                "tracking_summary": tracking_summary,
                "trajectory_summary": trajectory_summary,
            },
        )
        writer.write_run_manifest(effective_run_id, status="completed")

        return {
            "run_id": effective_run_id,
            "video_id": video_id,
            "status": "completed",
            "stage": "stage_4_trajectory_engine",
            "next_stage": "stage_5_event_engine_not_started",
            "total_frames_processed": detection_summary["total_frames_processed"],
            "total_detections": detection_summary["total_detections"],
            "total_tracks": tracking_summary["total_tracks"],
            "unique_track_ids": tracking_summary["unique_track_ids"],
            "total_trajectory_points": trajectory_summary["total_trajectory_points"],
            "per_class_counts": detection_summary["per_class_counts"],
            "per_class_track_counts": tracking_summary["per_class_track_counts"],
            "track_state_counts": tracking_summary["track_state_counts"],
            "trajectory_track_state_counts": trajectory_summary["track_state_counts"],
            "avg_track_length": trajectory_summary["avg_track_length"],
            "max_track_length": trajectory_summary["max_track_length"],
            "avg_speed_px_per_second": trajectory_summary["avg_speed_px_per_second"],
            "result_dir": str(run_dir),
            "artifacts": artifacts,
            "processing_config_snapshot": effective_params.config_snapshot,
        }


def _build_detector_config(
    params: TrajectoryRunParams,
    settings: Any,
) -> dict[str, Any]:
    return {
        "model_path": params.model_path or settings.yolo_model_path,
        "conf_threshold": (
            params.conf_threshold
            if params.conf_threshold is not None
            else settings.yolo_conf_threshold
        ),
        "iou_threshold": (
            params.iou_threshold
            if params.iou_threshold is not None
            else settings.yolo_iou_threshold
        ),
        "image_size": (
            params.image_size
            if params.image_size is not None
            else settings.yolo_image_size
        ),
        "device": params.device or settings.yolo_device,
        "dry_run": (
            params.detector_dry_run
            if params.detector_dry_run is not None
            else settings.yolo_dry_run
        ),
    }


def _build_tracker_config(
    params: TrajectoryRunParams,
    settings: Any,
) -> dict[str, Any]:
    target_classes = (
        params.tracking_target_classes
        if params.tracking_target_classes is not None
        else settings.tracking_target_classes
    )
    return {
        "dry_run": (
            params.tracker_dry_run
            if params.tracker_dry_run is not None
            else settings.deepsort_dry_run
        ),
        "max_age": (
            params.deepsort_max_age
            if params.deepsort_max_age is not None
            else settings.deepsort_max_age
        ),
        "n_init": (
            params.deepsort_n_init
            if params.deepsort_n_init is not None
            else settings.deepsort_n_init
        ),
        "max_iou_distance": (
            params.deepsort_max_iou_distance
            if params.deepsort_max_iou_distance is not None
            else settings.deepsort_max_iou_distance
        ),
        "max_cosine_distance": (
            params.deepsort_max_cosine_distance
            if params.deepsort_max_cosine_distance is not None
            else settings.deepsort_max_cosine_distance
        ),
        "target_classes": list(target_classes),
        "min_confidence": (
            params.tracking_min_confidence
            if params.tracking_min_confidence is not None
            else settings.tracking_min_confidence
        ),
    }


def _build_trajectory_config(
    params: TrajectoryRunParams,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    metadata_fps = float(metadata.get("fps") or 0.0)
    fps = params.fps if params.fps is not None else metadata_fps or None
    return {
        "fps": fps,
        "direction_window": params.direction_window,
        "dwell_speed_threshold": params.dwell_speed_threshold,
        "max_history_points": params.max_history_points,
    }


def _validate_frame_limits(frame_stride: int, max_frames: int | None) -> None:
    if frame_stride <= 0:
        raise ValueError("frame_stride must be greater than 0")
    if max_frames is not None and max_frames < 0:
        raise ValueError("max_frames must be greater than or equal to 0")


def _read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
