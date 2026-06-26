from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ProcessingTask
from app.repositories import ProcessingTaskRepository
from app.schemas.processing import ProcessingTaskResponse
from app.services.processing_service import processing_service


router = APIRouter(prefix="/api/processing", tags=["processing"])


@router.get("/tasks", response_model=list[ProcessingTaskResponse])
def list_processing_tasks(
    video_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    include_memory: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ProcessingTaskResponse]:
    tasks = ProcessingTaskRepository(db).list_filtered(
        video_id=video_id,
        run_id=run_id,
        status=status,
        mode=mode,
        task_type=task_type,
    )
    responses = [_task_response(task) for task in tasks]
    if include_memory:
        responses.extend(
            _memory_task_response(task)
            for task in processing_service.list_tasks()
            if _memory_task_matches(
                task,
                video_id=video_id,
                run_id=run_id,
                status=status,
                mode=mode,
                task_type=task_type,
            )
        )
    return responses


def _task_response(task: ProcessingTask) -> ProcessingTaskResponse:
    result = task.result or {}
    parameters = task.parameters or {}
    return ProcessingTaskResponse(
        id=task.id,
        video_id=task.video_id,
        run_id=str(result.get("run_id") or parameters.get("run_id") or ""),
        task_type=_task_type(task),
        mode=task.mode,
        status=task.status,
        params_json=parameters,
        progress=task.progress,
        error_message=task.error_message,
        started_at=_to_iso(task.started_at) if task.started_at else None,
        finished_at=_to_iso(task.finished_at) if task.finished_at else None,
        created_at=_to_iso(task.created_at),
        result=result,
    )


def _task_type(task: ProcessingTask) -> str:
    result = task.result or {}
    parameters = task.parameters or {}
    if result.get("task_type"):
        return str(result["task_type"])
    if parameters.get("task_type"):
        return str(parameters["task_type"])
    if task.mode == "realtime_process":
        return "realtime_process"
    return "offline_process"


def _memory_task_response(task: dict[str, Any]) -> ProcessingTaskResponse:
    params = task.get("params_json") or {}
    result = task.get("result") or {}
    return ProcessingTaskResponse(
        id=str(task["id"]),
        video_id=str(task["video_id"]),
        run_id=str(task.get("run_id") or result.get("run_id") or params.get("run_id") or ""),
        task_type=str(task.get("task_type") or params.get("task_type") or "offline_process"),
        mode=task.get("mode") or params.get("mode"),
        status=str(task["status"]),
        params_json=params,
        progress=float(task.get("progress") or 0.0),
        error_message=task.get("error_message"),
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
        created_at=str(task["created_at"]),
        result=result,
    )


def _memory_task_matches(
    task: dict[str, Any],
    *,
    video_id: str | None,
    run_id: str | None,
    status: str | None,
    mode: str | None,
    task_type: str | None,
) -> bool:
    response = _memory_task_response(task)
    if video_id and response.video_id != video_id:
        return False
    if run_id and response.run_id != run_id:
        return False
    if status and response.status != status:
        return False
    if mode and response.mode != mode:
        return False
    if task_type and response.task_type != task_type and response.mode != task_type:
        return False
    return True


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return normalized.replace(microsecond=0).isoformat()
    return value.replace(microsecond=0).isoformat() if hasattr(value, "isoformat") else str(value)
