from typing import Any

from pydantic import BaseModel


class ProcessingTaskResponse(BaseModel):
    id: str
    video_id: str
    run_id: str
    task_type: str
    status: str
    params_json: dict[str, Any]
    progress: float
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str
