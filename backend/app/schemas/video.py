from typing import Any

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    output_path: str | None = None
    status: str
    fps: float
    width: int
    height: int
    duration_seconds: float
    total_frames: int
    camera_id: str | None = None
    process_mode: str = "offline"
    created_at: str
    updated_at: str


class VideoStatusResponse(BaseModel):
    video_id: str
    status: str
    latest_task: dict[str, Any] | None = None
