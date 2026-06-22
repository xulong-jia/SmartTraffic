from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import ConfigResponse, HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="smarttraffic-api")


@router.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    settings = get_settings()
    return ConfigResponse(
        project_name=settings.project_name,
        yolo_model_path=settings.yolo_model_path,
        yolo_confidence_threshold=settings.yolo_confidence_threshold,
        yolo_iou_threshold=settings.yolo_iou_threshold,
        yolo_device=settings.yolo_device,
        frame_stride=settings.frame_stride,
        dry_run=settings.dry_run,
    )
