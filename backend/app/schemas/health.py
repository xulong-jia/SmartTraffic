from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ConfigResponse(BaseModel):
    project_name: str
    yolo_model_path: str
    yolo_confidence_threshold: float
    yolo_iou_threshold: float
    yolo_image_size: int
    yolo_device: str
    deepsort_dry_run: bool
    deepsort_max_age: int
    deepsort_n_init: int
    tracking_min_confidence: float
    tracking_target_classes: list[str]
    frame_stride: int
    dry_run: bool
