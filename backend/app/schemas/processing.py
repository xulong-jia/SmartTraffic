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
    direction_window: int | None = None
    dwell_speed_threshold: float | None = None
    max_history_points: int | None = None
    event_rules: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None
    run_events: bool = True
    generate_alerts: bool = True
    record_not_matched: bool = False


class ProcessingTaskResponse(BaseModel):
    id: str
    video_id: str
    run_id: str
    task_type: str
    mode: str | None = None
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
    total_trajectory_points: int | None = None
    per_class_counts: dict[str, int]
    per_class_track_counts: dict[str, int] | None = None
    track_state_counts: dict[str, int] | None = None
    trajectory_track_state_counts: dict[str, int] | None = None
    avg_track_length: float | None = None
    max_track_length: int | None = None
    avg_speed_px_per_second: float | None = None
    artifacts: dict[str, str]
