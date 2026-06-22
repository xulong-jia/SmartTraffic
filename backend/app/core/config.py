from dataclasses import dataclass
import os
from pathlib import Path

from app.core.paths import LOCAL_MODELS_DIR, LOCAL_VIDEOS_DIR, RESULTS_DIR


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_name: str = "SmartTraffic 智慧交通事件检测系统"
    yolo_model_path: str = "local_models/best.pt"
    yolo_confidence_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    yolo_device: str = "cpu"
    frame_stride: int = 1
    dry_run: bool = True
    local_videos_dir: Path = LOCAL_VIDEOS_DIR
    traffic_results_dir: Path = RESULTS_DIR
    local_models_dir: Path = LOCAL_MODELS_DIR
    cors_allow_origins: list[str] | None = None
    allowed_video_extensions: tuple[str, ...] = (
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm",
    )

    def __post_init__(self) -> None:
        if self.cors_allow_origins is None:
            object.__setattr__(
                self,
                "cors_allow_origins",
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ],
            )


def get_settings() -> Settings:
    cors = os.environ.get("CORS_ALLOW_ORIGINS", "")
    cors_allow_origins = (
        [origin.strip() for origin in cors.split(",") if origin.strip()]
        if cors.strip()
        else None
    )
    return Settings(
        project_name=os.environ.get(
            "PROJECT_NAME",
            "SmartTraffic 智慧交通事件检测系统",
        ),
        yolo_model_path=os.environ.get("YOLO_MODEL_PATH", "local_models/best.pt"),
        yolo_confidence_threshold=_float_env("YOLO_CONFIDENCE_THRESHOLD", 0.25),
        yolo_iou_threshold=_float_env("YOLO_IOU_THRESHOLD", 0.45),
        yolo_device=os.environ.get("YOLO_DEVICE", "cpu"),
        frame_stride=_int_env("FRAME_STRIDE", 1),
        dry_run=_bool_env("SMARTTRAFFIC_DRY_RUN", True),
        local_videos_dir=Path(os.environ.get("LOCAL_VIDEOS_DIR", str(LOCAL_VIDEOS_DIR))),
        traffic_results_dir=Path(
            os.environ.get("TRAFFIC_RESULTS_DIR", str(RESULTS_DIR))
        ),
        local_models_dir=Path(os.environ.get("LOCAL_MODELS_DIR", str(LOCAL_MODELS_DIR))),
        cors_allow_origins=cors_allow_origins,
    )
