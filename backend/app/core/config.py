from dataclasses import dataclass
import os
from pathlib import Path

from app.core.paths import LOCAL_MODELS_DIR, LOCAL_VIDEOS_DIR, PROJECT_DIR, RESULTS_DIR


def _env(name: str, default: str, *aliases: str) -> str:
    for key in (name, *aliases):
        value = os.environ.get(key)
        if value is not None:
            return value
    return default


def _float_env(name: str, default: float, *aliases: str) -> float:
    value = _env(name, str(default), *aliases)
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int, *aliases: str) -> int:
    value = _env(name, str(default), *aliases)
    try:
        return int(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool, *aliases: str) -> bool:
    value = _env(name, "true" if default else "false", *aliases)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: Path, *aliases: str) -> Path:
    value = _env(name, str(default.relative_to(PROJECT_DIR)), *aliases)
    path = Path(value)
    return path if path.is_absolute() else PROJECT_DIR / path


def _csv_env(name: str, default: tuple[str, ...], *aliases: str) -> tuple[str, ...]:
    value = _env(name, ",".join(default), *aliases)
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = "SmartTraffic 智慧交通事件检测系统"
    environment: str = "local"
    results_dir: Path = RESULTS_DIR
    local_videos_dir: Path = LOCAL_VIDEOS_DIR
    local_models_dir: Path = LOCAL_MODELS_DIR
    database_url: str = "sqlite:///./smarttraffic.db"
    auth_mode: str = "permissive"
    yolo_model_path: str = "local_models/best.pt"
    yolo_conf_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    yolo_image_size: int = 640
    yolo_device: str = "cpu"
    yolo_dry_run: bool = True
    deepsort_dry_run: bool = True
    deepsort_max_age: int = 30
    deepsort_n_init: int = 1
    deepsort_max_iou_distance: float = 0.7
    deepsort_max_cosine_distance: float = 0.2
    tracking_min_confidence: float = 0.0
    tracking_target_classes: tuple[str, ...] = (
        "car",
        "bus",
        "truck",
        "motorcycle",
        "bicycle",
        "person",
    )
    tracking_write_preview: bool = False
    video_frame_stride: int = 1
    detection_max_frames: int | None = None
    cors_allow_origins: list[str] | None = None
    allowed_video_extensions: tuple[str, ...] = (
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm",
    )
    max_upload_mb: int = 200
    max_video_duration_seconds: float = 600.0
    allowed_video_codecs: tuple[str, ...] = (
        "avc1",
        "h264",
        "mp4v",
        "xvid",
        "mjpg",
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

    @property
    def project_name(self) -> str:
        return self.app_name

    @property
    def traffic_results_dir(self) -> Path:
        return self.results_dir

    @property
    def yolo_confidence_threshold(self) -> float:
        return self.yolo_conf_threshold

    @property
    def frame_stride(self) -> int:
        return self.video_frame_stride

    @property
    def dry_run(self) -> bool:
        return self.yolo_dry_run

    @property
    def tracker_dry_run(self) -> bool:
        return self.deepsort_dry_run


def get_settings() -> Settings:
    cors = os.environ.get("CORS_ALLOW_ORIGINS", "")
    cors_allow_origins = (
        [origin.strip() for origin in cors.split(",") if origin.strip()]
        if cors.strip()
        else None
    )
    return Settings(
        app_name=_env("SMARTTRAFFIC_APP_NAME", "SmartTraffic 智慧交通事件检测系统", "PROJECT_NAME"),
        environment=_env("SMARTTRAFFIC_ENV", "local"),
        results_dir=_path_env("SMARTTRAFFIC_RESULTS_DIR", RESULTS_DIR, "TRAFFIC_RESULTS_DIR"),
        local_videos_dir=_path_env("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", LOCAL_VIDEOS_DIR, "LOCAL_VIDEOS_DIR"),
        local_models_dir=_path_env("SMARTTRAFFIC_LOCAL_MODELS_DIR", LOCAL_MODELS_DIR, "LOCAL_MODELS_DIR"),
        database_url=_env("SMARTTRAFFIC_DATABASE_URL", "sqlite:///./smarttraffic.db"),
        auth_mode=_env("SMARTTRAFFIC_AUTH_MODE", "permissive").strip().lower(),
        yolo_model_path=os.environ.get("YOLO_MODEL_PATH", "local_models/best.pt"),
        yolo_conf_threshold=_float_env("YOLO_CONF_THRESHOLD", 0.25, "YOLO_CONFIDENCE_THRESHOLD"),
        yolo_iou_threshold=_float_env("YOLO_IOU_THRESHOLD", 0.45),
        yolo_image_size=_int_env("YOLO_IMAGE_SIZE", 640),
        yolo_device=os.environ.get("YOLO_DEVICE", "cpu"),
        yolo_dry_run=_bool_env("YOLO_DRY_RUN", True, "SMARTTRAFFIC_DRY_RUN"),
        deepsort_dry_run=_bool_env("DEEPSORT_DRY_RUN", True),
        deepsort_max_age=_int_env("DEEPSORT_MAX_AGE", 30),
        deepsort_n_init=_int_env("DEEPSORT_N_INIT", 1),
        deepsort_max_iou_distance=_float_env("DEEPSORT_MAX_IOU_DISTANCE", 0.7),
        deepsort_max_cosine_distance=_float_env("DEEPSORT_MAX_COSINE_DISTANCE", 0.2),
        tracking_min_confidence=_float_env("TRACKING_MIN_CONFIDENCE", 0.0),
        tracking_target_classes=_csv_env(
            "TRACKING_TARGET_CLASSES",
            ("car", "bus", "truck", "motorcycle", "bicycle", "person"),
        ),
        tracking_write_preview=_bool_env("TRACKING_WRITE_PREVIEW", False),
        video_frame_stride=_int_env("VIDEO_FRAME_STRIDE", 1, "FRAME_STRIDE"),
        detection_max_frames=(
            _int_env("DETECTION_MAX_FRAMES", 0) or None
        ),
        max_upload_mb=_int_env("SMARTTRAFFIC_MAX_UPLOAD_MB", 200),
        max_video_duration_seconds=_float_env(
            "SMARTTRAFFIC_MAX_VIDEO_DURATION_SECONDS",
            600.0,
        ),
        allowed_video_codecs=tuple(
            codec.lower()
            for codec in _csv_env(
                "SMARTTRAFFIC_ALLOWED_VIDEO_CODECS",
                ("avc1", "h264", "mp4v", "xvid", "mjpg"),
            )
        ),
        cors_allow_origins=cors_allow_origins,
    )
