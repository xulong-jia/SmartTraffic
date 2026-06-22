from pathlib import Path
from typing import Any


def validate_video_path(video_path: str | Path) -> Path:
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"video path does not exist: {path}")
    if path.is_dir():
        raise ValueError(f"video path must be a file, got directory: {path}")
    return path


def read_video_metadata(video_path: str | Path) -> dict[str, Any]:
    path = validate_video_path(video_path)
    cv2 = _import_cv2()

    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError(f"unable to open video: {path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()

    return {
        "video_path": str(path),
        "filename": path.name,
        "fps": fps,
        "width": width,
        "height": height,
        "total_frames": total_frames,
        "duration_seconds": total_frames / fps if fps > 0 else 0.0,
        "backend": "opencv",
    }


def iter_frames(video_path: str | Path, frame_stride: int = 1):
    if frame_stride <= 0:
        raise ValueError("frame_stride must be greater than 0")
    path = validate_video_path(video_path)
    cv2 = _import_cv2()
    capture = cv2.VideoCapture(str(path))
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % frame_stride == 0:
                timestamp_ms = int(capture.get(cv2.CAP_PROP_POS_MSEC))
                yield {
                    "frame_index": frame_index,
                    "timestamp_ms": timestamp_ms,
                    "frame": frame,
                }
            frame_index += 1
    finally:
        capture.release()


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to read video metadata") from exc
    return cv2
