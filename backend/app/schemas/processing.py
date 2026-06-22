from typing import Any

from pydantic import BaseModel


class DetectionProcessRequest(BaseModel):
    mode: str = "detection_tracking"
    dry_run: bool | None = None
    detector_dry_run: bool | None = None
    tracker_dry_run: bool | None = None
    frame_stride: int | None = None
    max_frames: int | None = None
    conf_threshold: float | None = None
    iou_threshold: float | None = None
    image_size: int | None = None
    device: str | None = None
    model_path: str | None = None
    write_preview: bool | None = None
    deepsort_max_age: int | None = None
    deepsort_n_init: int | None = None
    deepsort_max_iou_distance: float | None = None
    deepsort_max_cosine_distance: float | None = None
    tracking_min_confidence: float | None = None
    tracking_target_classes: list[str] | None = None


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
    total_tracks: int | None = None
    unique_track_ids: int | None = None
    per_class_counts: dict[str, int]
    per_class_track_counts: dict[str, int] | None = None
    track_state_counts: dict[str, int] | None = None
    artifacts: dict[str, str]
