from typing import Any

from app.models import ProcessingTask
from app.repositories.base import BaseRepository


class ProcessingTaskRepository(BaseRepository[ProcessingTask]):
    model = ProcessingTask

    def update_status(
        self,
        task_id: str,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ProcessingTask | None:
        values: dict[str, Any] = {"status": status}
        if result is not None:
            values["result"] = result
        if error_message is not None:
            values["error_message"] = error_message
        return self.update(task_id, **values)
