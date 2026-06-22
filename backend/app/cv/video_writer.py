from pathlib import Path
from typing import Any


def draw_detections(frame: Any, detections: list[dict[str, Any]]) -> Any:
    cv2 = _import_cv2()
    output = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = [int(round(value)) for value in detection["bbox"]]
        class_name = str(detection.get("class_name", "object"))
        confidence = float(detection.get("confidence", 0.0))
        label = f"{class_name} {confidence:.2f}"
        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 180, 80), 2)
        cv2.putText(
            output,
            label,
            (x1, max(12, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 180, 80),
            1,
            cv2.LINE_AA,
        )
    return output


def draw_tracks(frame: Any, tracks: list[dict[str, Any]]) -> Any:
    cv2 = _import_cv2()
    output = frame.copy()
    for track in tracks:
        x1, y1, x2, y2 = [int(round(value)) for value in track["bbox"]]
        track_id = track.get("track_id")
        class_name = str(track.get("class_name", "object"))
        confidence = float(track.get("confidence", 0.0))
        label = f"#{track_id} {class_name} {confidence:.2f}"
        cv2.rectangle(output, (x1, y1), (x2, y2), (40, 120, 240), 2)
        cv2.putText(
            output,
            label,
            (x1, max(12, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (40, 120, 240),
            1,
            cv2.LINE_AA,
        )
    return output


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
