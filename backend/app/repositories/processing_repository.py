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
