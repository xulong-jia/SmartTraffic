from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.services.detection_service import DetectionRunParams, DetectionService
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.video_service import video_registry


class ProcessingService:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def create_processing_task(
        self,
        video: dict[str, Any],
        params: DetectionRunParams | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        run_id = f"run_{uuid4().hex[:12]}"
        now = _utc_now_iso()
        task = {
            "id": uuid4().hex,
            "video_id": video["id"],
            "run_id": run_id,
            "task_type": "offline_process",
            "status": "running",
            "params_json": {
                "frame_stride": params.frame_stride if params else settings.frame_stride,
                "dry_run": params.dry_run if params and params.dry_run is not None else settings.dry_run,
                "stage": "stage_2_yolov8_detection",
                "next_stage": "stage_3_deepsort_tracking_not_started",
            },
            "progress": 0.0,
            "error_message": None,
            "started_at": now,
            "finished_at": None,
            "created_at": now,
        }
        self._tasks[task["id"]] = task
        try:
            video_registry.update_status(video["id"], "processing")
            result = DetectionService(results_dir=settings.results_dir).run_detection(
                video_id=video["id"],
                video_path=video["file_path"],
                run_id=run_id,
                params=params,
            )
            task.update(
                {
                    "status": "completed",
                    "progress": 1.0,
                    "finished_at": _utc_now_iso(),
                    "result": result,
                }
            )
            video_registry.update_status(video["id"], "completed")
            traffic_analysis_service.register_run(
                run_id=run_id,
                video_id=video["id"],
                result_dir=result["result_dir"],
                artifact_index=result["artifacts"],
                status="completed",
            )
            return dict(task)
        except Exception as exc:
            task.update(
                {
                    "status": "failed",
                    "finished_at": _utc_now_iso(),
                    "error_message": str(exc),
                }
            )
            video_registry.update_status(video["id"], "failed")
            raise

    def list_tasks(self) -> list[dict[str, Any]]:
        return sorted(self._tasks.values(), key=lambda item: item["created_at"])

    def get_latest_task(self, video_id: str) -> dict[str, Any] | None:
        matches = [task for task in self._tasks.values() if task["video_id"] == video_id]
        if not matches:
            return None
        return dict(sorted(matches, key=lambda item: item["created_at"])[-1])

    def clear(self) -> None:
        self._tasks.clear()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


processing_service = ProcessingService()
