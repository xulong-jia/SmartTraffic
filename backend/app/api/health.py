from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.health import ConfigResponse, HealthResponse, ReadinessResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="smarttraffic-api")


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)) -> ReadinessResponse | JSONResponse:
    checks: dict[str, str] = {"app": "ok"}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "service": "smarttraffic-api",
                "checks": checks,
            },
        )
    return ReadinessResponse(
        status="ok",
        service="smarttraffic-api",
        checks=checks,
    )


@router.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    settings = get_settings()
    return ConfigResponse(
        project_name=settings.project_name,
        yolo_model_path=settings.yolo_model_path,
        yolo_confidence_threshold=settings.yolo_confidence_threshold,
        yolo_iou_threshold=settings.yolo_iou_threshold,
        yolo_image_size=settings.yolo_image_size,
        yolo_device=settings.yolo_device,
        deepsort_dry_run=settings.deepsort_dry_run,
        deepsort_max_age=settings.deepsort_max_age,
        deepsort_n_init=settings.deepsort_n_init,
        tracking_min_confidence=settings.tracking_min_confidence,
        tracking_target_classes=list(settings.tracking_target_classes),
        frame_stride=settings.frame_stride,
        dry_run=settings.dry_run,
    )
