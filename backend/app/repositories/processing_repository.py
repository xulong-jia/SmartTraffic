from typing import Any

from sqlalchemy import select

from app.models import ProcessingTask
from app.repositories.base import BaseRepository


class ProcessingTaskRepository(BaseRepository[ProcessingTask]):
    model = ProcessingTask

    def update_status(
        self,
        task_id: str,
        status: str,
        *,
        progress: float | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        started_at: Any | None = None,
        finished_at: Any | None = None,
    ) -> ProcessingTask | None:
        values: dict[str, Any] = {"status": status}
        if progress is not None:
            values["progress"] = progress
        if result is not None:
            values["result"] = result
        if error_message is not None:
            values["error_message"] = error_message
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        return self.update(task_id, **values)

    def get_latest_for_video(self, video_id: str) -> ProcessingTask | None:
        statement = (
            select(ProcessingTask)
            .where(ProcessingTask.video_id == video_id)
            .order_by(ProcessingTask.created_at.desc(), ProcessingTask.id.desc())
            .limit(1)
        )
        return self.session.scalars(statement).first()

    def list_filtered(
        self,
        *,
        video_id: str | None = None,
        run_id: str | None = None,
        status: str | None = None,
        mode: str | None = None,
        task_type: str | None = None,
    ) -> list[ProcessingTask]:
        statement = select(ProcessingTask)
        if video_id:
            statement = statement.where(ProcessingTask.video_id == video_id)
        if status:
            statement = statement.where(ProcessingTask.status == status)
        if mode:
            statement = statement.where(ProcessingTask.mode == mode)
        statement = statement.order_by(ProcessingTask.created_at, ProcessingTask.id)
        tasks = list(self.session.scalars(statement).all())
        if run_id:
            tasks = [
                task
                for task in tasks
                if _task_run_id(task) == run_id
            ]
        if task_type:
            tasks = [
                task
                for task in tasks
                if _task_type(task) == task_type or task.mode == task_type
            ]
        return tasks


def _task_run_id(task: ProcessingTask) -> str:
    result = task.result or {}
    parameters = task.parameters or {}
    return str(result.get("run_id") or parameters.get("run_id") or "")


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
