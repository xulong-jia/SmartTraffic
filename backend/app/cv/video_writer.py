from pathlib import Path
from typing import Any


class AnnotatedVideoWriter:
    """Minimal OpenCV video writer wrapper for future annotated outputs."""

    def __init__(
        self,
        output_path: str | Path,
        fps: float,
        frame_size: tuple[int, int],
        codec: str = "mp4v",
    ) -> None:
        cv2 = _import_cv2()
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = cv2.VideoWriter(
            str(self.output_path),
            cv2.VideoWriter_fourcc(*codec),
            fps,
            frame_size,
        )
        if not self._writer.isOpened():
            raise ValueError(f"unable to open video writer: {self.output_path}")

    def write_frame(self, frame: Any) -> None:
        self._writer.write(frame)

    def release(self) -> None:
        self._writer.release()

    def __enter__(self) -> "AnnotatedVideoWriter":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to write annotated videos") from exc
    return cv2
