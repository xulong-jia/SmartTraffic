from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import ProcessingTaskRepository, TrafficAnalysisRunRepository
from app.services.alert_service import AlertService
from app.services.detection_service import DetectionRunParams, DetectionService
from app.services.event_service import EventRunParams, EventService
from app.services.traffic_analysis_service import traffic_analysis_service
from app.services.trajectory_service import TrajectoryRunParams, TrajectoryService
from app.services.tracking_service import TrackingRunParams, TrackingService
from app.services.video_service import VideoDbService, video_registry


@dataclass(frozen=True)
class EventAlertProcessParams:
    event_rules: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None
    run_events: bool = True
    generate_alerts: bool = True
    record_not_matched: bool = False


class ProcessingService:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def create_processing_task(
        self,
        video: dict[str, Any],
        params: DetectionRunParams | TrackingRunParams | TrajectoryRunParams | None = None,
        mode: str = "detection_tracking",
        event_alert_params: EventAlertProcessParams | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        if mode not in {
            "detection_only",
            "detection_tracking",
            "detection_tracking_trajectory",
        }:
            raise ValueError(
                "mode must be detection_only, detection_tracking, "
                "or detection_tracking_trajectory"
            )
        run_id = f"run_{uuid4().hex[:12]}"
        now = _utc_now()
        now_iso = _to_iso(now)
        stage, next_stage = _stage_for_mode(mode)
        task = {
            "id": uuid4().hex,
            "video_id": video["id"],
            "run_id": run_id,
            "task_type": "offline_process",
            "status": "pending",
            "params_json": {
                "frame_stride": params.frame_stride if params else settings.frame_stride,
                "mode": mode,
                "stage": stage,
                "next_stage": next_stage,
            },
            "progress": 0.0,
            "error_message": None,
            "started_at": None,
            "finished_at": None,
            "created_at": now_iso,
        }
        task_repo: ProcessingTaskRepository | None = None
        video_service: VideoDbService | None = None
        if db is None:
            self._tasks[task["id"]] = task
        else:
            task_repo = ProcessingTaskRepository(db)
            video_service = VideoDbService(db)
            task_repo.create(
                id=task["id"],
                video_id=video["id"],
                status="pending",
                mode=mode,
                parameters=task["params_json"],
                progress=0.0,
            )
        try:
            started_at = _utc_now()
            task.update(
                {
                    "status": "running",
                    "progress": 0.1,
                    "started_at": _to_iso(started_at),
                }
            )
            if db is None:
                video_registry.update_status(video["id"], "processing")
            else:
                assert task_repo is not None
                assert video_service is not None
                task_repo.update_status(
                    task["id"],
                    "running",
                    progress=0.1,
                    started_at=started_at,
                )
                video_service.update_status(video["id"], "processing")
            if mode == "detection_only":
                detection_params = (
                    params if isinstance(params, DetectionRunParams) else None
                )
                result = DetectionService(results_dir=settings.results_dir).run_detection(
                    video_id=video["id"],
                    video_path=video["file_path"],
                    run_id=run_id,
                    params=detection_params,
                )
            elif mode == "detection_tracking":
                tracking_params = (
                    params if isinstance(params, TrackingRunParams) else None
                )
                result = TrackingService(results_dir=settings.results_dir).run_tracking(
                    video_id=video["id"],
                    video_path=video["file_path"],
                    run_id=run_id,
                    params=tracking_params,
                )
            else:
                trajectory_params = (
                    params if isinstance(params, TrajectoryRunParams) else None
                )
                result = TrajectoryService(
                    results_dir=settings.results_dir
                ).run_trajectory(
                    video_id=video["id"],
                    video_path=video["file_path"],
                    run_id=run_id,
                    params=trajectory_params,
                )
                result = _run_event_alert_pipeline(
                    run_id=run_id,
                    video_id=video["id"],
                    result=result,
                    params=event_alert_params,
                )
            task.update(
                {
                    "status": "completed",
                    "progress": 1.0,
                    "finished_at": _to_iso(_utc_now()),
                    "result": result,
                }
            )
            if db is None:
                video_registry.update_status(video["id"], "completed")
            else:
                assert task_repo is not None
                assert video_service is not None
                task_repo.update_status(
                    task["id"],
                    "completed",
                    progress=1.0,
                    result=result,
                    finished_at=_parse_iso(task["finished_at"]),
                )
                video_service.update_status(video["id"], "completed")
                TrafficAnalysisRunRepository(db).create(
                    id=run_id,
                    video_id=video["id"],
                    status="completed",
                    result_dir=f"results/traffic_analysis/{run_id}",
                    artifact_index=result["artifacts"],
                    summary=result,
                )
            traffic_analysis_service.register_run(
                run_id=run_id,
                video_id=video["id"],
                result_dir=f"results/traffic_analysis/{run_id}",
                artifact_index=result["artifacts"],
                status="completed",
            )
            return dict(task)
        except Exception as exc:
            task.update(
                {
                    "status": "failed",
                    "finished_at": _to_iso(_utc_now()),
                    "error_message": str(exc),
                }
            )
            if db is None:
                video_registry.update_status(video["id"], "failed")
            else:
                assert task_repo is not None
                assert video_service is not None
                task_repo.update_status(
                    task["id"],
                    "failed",
                    error_message=str(exc),
                    finished_at=_parse_iso(task["finished_at"]),
                )
                video_service.update_status(video["id"], "failed")
            raise

    def list_tasks(self) -> list[dict[str, Any]]:
        return sorted(self._tasks.values(), key=lambda item: item["created_at"])

    def get_latest_task(self, video_id: str) -> dict[str, Any] | None:
        matches = [task for task in self._tasks.values() if task["video_id"] == video_id]
        if not matches:
            return None
        return dict(sorted(matches, key=lambda item: item["created_at"])[-1])

    def get_latest_db_task(
        self,
        video_id: str,
        db: Session,
    ) -> dict[str, Any] | None:
        task = ProcessingTaskRepository(db).get_latest_for_video(video_id)
        if task is None:
            return None
        return {
            "id": task.id,
            "video_id": task.video_id,
            "run_id": (task.result or {}).get("run_id", ""),
            "task_type": "offline_process",
            "status": task.status,
            "params_json": task.parameters or {},
            "progress": task.progress,
            "error_message": task.error_message,
            "started_at": _to_iso(task.started_at) if task.started_at else None,
            "finished_at": _to_iso(task.finished_at) if task.finished_at else None,
            "created_at": _to_iso(task.created_at),
            "result": task.result,
        }

    def clear(self) -> None:
        self._tasks.clear()


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _stage_for_mode(mode: str) -> tuple[str, str]:
    if mode == "detection_only":
        return "stage_2_yolov8_detection", "stage_3_deepsort_tracking_not_started"
    if mode == "detection_tracking":
        return "stage_3_deepsort_tracking", "stage_4_trajectory_engine_not_started"
    return "stage_4_trajectory_engine", "stage_5_event_engine_not_started"


processing_service = ProcessingService()


def _run_event_alert_pipeline(
    *,
    run_id: str,
    video_id: str,
    result: dict[str, Any],
    params: EventAlertProcessParams | None,
) -> dict[str, Any]:
    effective_params = params or EventAlertProcessParams()
    if not effective_params.run_events:
        return result

    merged_result = dict(result)
    event_result = EventService().run_events(
        run_id=run_id,
        video_id=video_id,
        params=EventRunParams(
            rules=effective_params.event_rules,
            zones=effective_params.zones,
            record_not_matched=effective_params.record_not_matched,
        ),
    )
    merged_result["total_events"] = event_result["total_events"]
    merged_result["event_summary"] = event_result["event_summary"]
    merged_result["artifacts"] = event_result["artifacts"]

    if effective_params.generate_alerts:
        alert_result = AlertService().generate_alerts(run_id=run_id)
        merged_result["total_alerts"] = alert_result["total_alerts"]
        merged_result["alert_summary"] = alert_result["alert_summary"]
        merged_result["artifacts"] = alert_result["artifacts"]

    return merged_result
