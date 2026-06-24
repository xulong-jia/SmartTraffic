from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings
from app.cv.frame_reader import iter_frames, read_video_metadata
from app.cv.video_writer import AnnotatedVideoWriter, draw_detections
from app.cv.yolo_detector import YoloDetector


@dataclass(frozen=True)
class DetectionRunParams:
    model_path: str | None = None
    conf_threshold: float | None = None
    iou_threshold: float | None = None
    image_size: int | None = None
    device: str | None = None
    dry_run: bool | None = None
    frame_stride: int | None = None
    max_frames: int | None = None
    write_preview: bool = False


class DetectionService:
    def __init__(
        self,
        detector: YoloDetector | None = None,
        results_dir: str | Path | None = None,
    ) -> None:
        self.detector = detector
        self.results_dir = Path(results_dir) if results_dir is not None else None

    def run_detection(
        self,
        video_id: str,
        video_path: str | Path,
        run_id: str | None = None,
        params: DetectionRunParams | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        effective_params = params or DetectionRunParams()
        effective_run_id = run_id or f"run_{uuid4().hex[:12]}"
        results_dir = self.results_dir or settings.results_dir
        writer = TrafficArtifactWriter(results_dir)
        metadata = read_video_metadata(video_path)
        started_at = _utc_now_iso()

        detector_config = {
            "model_path": effective_params.model_path or settings.yolo_model_path,
            "conf_threshold": (
                effective_params.conf_threshold
                if effective_params.conf_threshold is not None
                else settings.yolo_conf_threshold
            ),
            "iou_threshold": (
                effective_params.iou_threshold
                if effective_params.iou_threshold is not None
                else settings.yolo_iou_threshold
            ),
            "image_size": (
                effective_params.image_size
                if effective_params.image_size is not None
                else settings.yolo_image_size
            ),
            "device": effective_params.device or settings.yolo_device,
            "dry_run": (
                effective_params.dry_run
                if effective_params.dry_run is not None
                else settings.yolo_dry_run
            ),
        }
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

        run_dir = writer.create_run_directory(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": str(video_path),
                "mode": "offline",
                "stage": "stage_2_yolov8_detection",
                "detector_config": detector_config,
                "started_at": started_at,
                "finished_at": "",
                "video_metadata": metadata,
            },
        )

        detector = self.detector or YoloDetector(**detector_config)
        frame_results: list[dict[str, Any]] = []
        preview_writer: AnnotatedVideoWriter | None = None
        if effective_params.write_preview:
            preview_writer = AnnotatedVideoWriter(
                run_dir / "detection_preview.mp4",
                fps=float(metadata["fps"] or 1.0),
                frame_size=(int(metadata["width"]), int(metadata["height"])),
            )

        try:
            for frame_item in iter_frames(
                video_path,
                frame_stride=frame_stride,
                max_frames=max_frames,
            ):
                result = detector.detect_frame(
                    frame_item["frame"],
                    frame_index=int(frame_item["frame_index"]),
                    timestamp_ms=int(frame_item["timestamp_ms"]),
                )
                frame_results.append(result)
                if preview_writer is not None:
                    preview_writer.write_frame(
                        draw_detections(frame_item["frame"], result["detections"])
                    )
        finally:
            if preview_writer is not None:
                preview_writer.release()

        artifacts = writer.write_detection_outputs(
            run_id=effective_run_id,
            video_id=video_id,
            frame_results=frame_results,
        )
        summary = _read_summary(artifacts["detection_summary"])
        finished_at = _utc_now_iso()
        artifact_index = writer.artifact_index(effective_run_id)
        writer.update_metadata(
            effective_run_id,
            {
                "video_id": video_id,
                "input_video": str(video_path),
                "mode": "offline",
                "stage": "stage_2_yolov8_detection",
                "detector_config": detector_config,
                "started_at": started_at,
                "finished_at": finished_at,
                "video_metadata": metadata,
                "artifacts": artifact_index,
                "detection_summary": summary,
            },
        )
        writer.write_run_manifest(effective_run_id, status="completed")

        return {
            "run_id": effective_run_id,
            "video_id": video_id,
            "status": "completed",
            "stage": "stage_2_yolov8_detection",
            "next_stage": "stage_3_deepsort_tracking_not_started",
            "total_frames_processed": summary["total_frames_processed"],
            "total_detections": summary["total_detections"],
            "per_class_counts": summary["per_class_counts"],
            "result_dir": str(run_dir),
            "artifacts": artifact_index,
        }


def _read_summary(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
