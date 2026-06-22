from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings
from app.cv.deepsort_tracker import DeepSortTracker
from app.cv.frame_reader import iter_frames, read_video_metadata
from app.cv.video_writer import AnnotatedVideoWriter, draw_tracks
from app.cv.yolo_detector import YoloDetector


@dataclass(frozen=True)
class TrackingRunParams:
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


class TrackingService:
    def __init__(
        self,
        detector: Any | None = None,
        tracker: DeepSortTracker | None = None,
        results_dir: str | Path | None = None,
    ) -> None:
        self.detector = detector
        self.tracker = tracker
        self.results_dir = Path(results_dir) if results_dir is not None else None

    def run_tracking(
        self,
        video_id: str,
        video_path: str | Path,
        run_id: str | None = None,
        params: TrackingRunParams | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        effective_params = params or TrackingRunParams()
        effective_run_id = run_id or f"run_{uuid4().hex[:12]}"
        results_dir = self.results_dir or settings.results_dir
        writer = TrafficArtifactWriter(results_dir)
        metadata = read_video_metadata(video_path)
        started_at = _utc_now_iso()

        detector_config = _build_detector_config(effective_params, settings)
        tracker_config = _build_tracker_config(effective_params, settings)
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
        write_preview = (
            effective_params.write_preview
            if effective_params.write_preview is not None
            else settings.tracking_write_preview
        )

        run_dir = writer.create_run_directory(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "mode": "offline",
                "stage": "stage_3_deepsort_tracking",
                "detector_config": detector_config,
                "tracker_config": tracker_config,
                "started_at": started_at,
                "finished_at": "",
                "video_metadata": metadata,
            },
        )

        detector = self.detector or YoloDetector(**detector_config)
        tracker = self.tracker or DeepSortTracker(**tracker_config)
        detection_frame_results: list[dict[str, Any]] = []
        tracking_frame_results: list[dict[str, Any]] = []
        preview_writer: AnnotatedVideoWriter | None = None
        if write_preview:
            preview_writer = AnnotatedVideoWriter(
                run_dir / "tracking_preview.mp4",
                fps=float(metadata["fps"] or 1.0),
                frame_size=(int(metadata["width"]), int(metadata["height"])),
            )

        try:
            for frame_item in iter_frames(
                video_path,
                frame_stride=frame_stride,
                max_frames=max_frames,
            ):
                detection_result = detector.detect_frame(
                    frame_item["frame"],
                    frame_index=int(frame_item["frame_index"]),
                    timestamp_ms=int(frame_item["timestamp_ms"]),
                )
                tracking_result = tracker.update(
                    frame_item["frame"],
                    detection_result["detections"],
                    frame_index=int(frame_item["frame_index"]),
                    timestamp_ms=int(frame_item["timestamp_ms"]),
                )
                detection_frame_results.append(detection_result)
                tracking_frame_results.append(tracking_result)
                if preview_writer is not None:
                    preview_writer.write_frame(
                        draw_tracks(frame_item["frame"], tracking_result["tracks"])
                    )
        finally:
            if preview_writer is not None:
                preview_writer.release()

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
        detection_summary = _read_json(detection_artifacts["detection_summary"])
        tracking_summary = _read_json(tracking_artifacts["tracking_summary"])
        finished_at = _utc_now_iso()
        artifact_index = writer.artifact_index(effective_run_id)
        writer.update_metadata(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": Path(video_path).name,
                "mode": "offline",
                "stage": "stage_3_deepsort_tracking",
                "detector_config": detector_config,
                "tracker_config": tracker.get_tracker_info()
                if hasattr(tracker, "get_tracker_info")
                else tracker_config,
                "started_at": started_at,
                "finished_at": finished_at,
                "video_metadata": metadata,
                "artifacts": artifact_index,
                "detection_summary": detection_summary,
                "tracking_summary": tracking_summary,
            },
        )

        return {
            "run_id": effective_run_id,
            "video_id": video_id,
            "status": "completed",
            "stage": "stage_3_deepsort_tracking",
            "next_stage": "stage_4_trajectory_engine_not_started",
            "total_frames_processed": tracking_summary["total_frames_processed"],
            "total_detections": detection_summary["total_detections"],
            "total_tracks": tracking_summary["total_tracks"],
            "unique_track_ids": tracking_summary["unique_track_ids"],
            "per_class_counts": detection_summary["per_class_counts"],
            "per_class_track_counts": tracking_summary["per_class_track_counts"],
            "track_state_counts": tracking_summary["track_state_counts"],
            "result_dir": str(run_dir),
            "artifacts": artifact_index,
        }


def _build_detector_config(params: TrackingRunParams, settings: Any) -> dict[str, Any]:
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


def _build_tracker_config(params: TrackingRunParams, settings: Any) -> dict[str, Any]:
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


def _read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
