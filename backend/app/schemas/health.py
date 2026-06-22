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
    frame_stride: int
    dry_run: bool
