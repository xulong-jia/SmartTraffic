from typing import Any

from pydantic import BaseModel


class DetectionProcessRequest(BaseModel):
    dry_run: bool | None = None
    frame_stride: int | None = None
    max_frames: int | None = None
    conf_threshold: float | None = None
    iou_threshold: float | None = None
    image_size: int | None = None
    device: str | None = None
    model_path: str | None = None
    write_preview: bool = False


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
    result: dict[str, Any] | None = None


class DetectionProcessResponse(BaseModel):
    run_id: str
    video_id: str
    status: str
    stage: str
    next_stage: str
    total_frames_processed: int
    total_detections: int
    per_class_counts: dict[str, int]
    artifacts: dict[str, str]
