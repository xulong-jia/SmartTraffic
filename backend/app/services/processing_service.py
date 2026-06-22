from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings
from app.services.traffic_analysis_service import traffic_analysis_service


class ProcessingService:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def create_processing_task(self, video: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        run_id = f"run_{uuid4().hex[:12]}"
        writer = TrafficArtifactWriter(settings.traffic_results_dir)
        run_dir = writer.create_run_directory(
            run_id=run_id,
            metadata={
                "video_id": video["id"],
                "input_video": video["file_path"],
                "fps": video["fps"],
                "width": video["width"],
                "height": video["height"],
                "detector_config": {
                    "model_path": settings.yolo_model_path,
                    "confidence_threshold": settings.yolo_confidence_threshold,
                    "iou_threshold": settings.yolo_iou_threshold,
                    "device": settings.yolo_device,
                    "dry_run": settings.dry_run,
                },
                "tracker_config": {},
                "event_config": {},
            },
        )
        traffic_analysis_service.register_run(
            run_id=run_id,
            video_id=video["id"],
            result_dir=str(run_dir),
            artifact_index=writer.artifact_index(run_id),
        )
        now = _utc_now_iso()
        task = {
            "id": uuid4().hex,
            "video_id": video["id"],
            "run_id": run_id,
            "task_type": "offline_process",
            "status": "pending",
            "params_json": {
                "frame_stride": settings.frame_stride,
                "dry_run": settings.dry_run,
            },
            "progress": 0.0,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
            "created_at": now,
        }
        self._tasks[task["id"]] = task
        return dict(task)

    def list_tasks(self) -> list[dict[str, Any]]:
        return sorted(self._tasks.values(), key=lambda item: item["created_at"])

    def get_latest_task(self, video_id: str) -> dict[str, Any] | None:
        matches = [task for task in self._tasks.values() if task["video_id"] == video_id]
        if not matches:
            return None
        return dict(sorted(matches, key=lambda item: item["created_at"])[-1])


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


processing_service = ProcessingService()
