from pathlib import Path
from typing import Any


class YoloDetector:
    """YOLOv8 detector adapter with a dry-run mode for phase-one wiring.

    The detector only owns model loading and detection formatting. Traffic
    events, tracking, trajectory features, and alerts belong to later modules.
    """

    def __init__(
        self,
        model_path: str = "",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "cpu",
        dry_run: bool = True,
    ) -> None:
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.dry_run = dry_run
        self._model: Any | None = None

    def detect_frame(
        self,
        frame: Any,
        frame_index: int,
        timestamp_ms: int | None = None,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "frame_index": frame_index,
                "timestamp_ms": timestamp_ms,
                "detections": [],
            }

        model = self._load_model()
        results = model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )
        result = results[0] if results else None
        return {
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "detections": self._format_result(result),
        }

    def detect_batch(
        self,
        frames: list[Any],
        start_frame_index: int = 0,
        timestamp_ms_values: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        outputs = []
        for offset, frame in enumerate(frames):
            timestamp_ms = (
                timestamp_ms_values[offset]
                if timestamp_ms_values and offset < len(timestamp_ms_values)
                else None
            )
            outputs.append(
                self.detect_frame(
                    frame,
                    frame_index=start_frame_index + offset,
                    timestamp_ms=timestamp_ms,
                )
            )
        return outputs

    @staticmethod
    def format_detection(raw: dict[str, Any]) -> dict[str, Any]:
        bbox = raw.get("bbox", [])
        if len(bbox) != 4:
            raise ValueError("bbox must contain four coordinates")
        return {
            "class_id": raw.get("class_id"),
            "class_name": str(raw.get("class_name", "")),
            "confidence": float(raw.get("confidence", 0.0)),
            "bbox": [float(value) for value in bbox],
        }

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not self.model_path:
            raise FileNotFoundError("YOLO model path is required when dry_run is false")
        if not Path(self.model_path).is_file():
            raise FileNotFoundError(f"YOLO model not found: {self.model_path}")
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is required for real YOLOv8 inference"
            ) from exc
        self._model = YOLO(self.model_path)
        return self._model

    def _format_result(self, result: Any) -> list[dict[str, Any]]:
        if result is None or getattr(result, "boxes", None) is None:
            return []

        boxes = result.boxes
        xyxy_values = _to_list(getattr(boxes, "xyxy", []))
        cls_values = _to_list(getattr(boxes, "cls", []))
        conf_values = _to_list(getattr(boxes, "conf", []))
        names = getattr(result, "names", {}) or {}

        detections = []
        for xyxy, cls_value, conf_value in zip(xyxy_values, cls_values, conf_values):
            coords = _to_list(xyxy)
            if len(coords) < 4:
                continue
            class_id = int(_to_scalar(cls_value))
            detections.append(
                self.format_detection(
                    {
                        "class_id": class_id,
                        "class_name": _class_name(names, class_id),
                        "confidence": _to_scalar(conf_value),
                        "bbox": coords[:4],
                    }
                )
            )
        return detections


def _to_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def _to_list(value: Any) -> list[Any]:
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    if hasattr(value, "tolist"):
        result = value.tolist()
        return result if isinstance(result, list) else [result]
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return value
    return [value]


def _class_name(names: dict[Any, str] | list[str] | tuple[str, ...], class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, names.get(str(class_id), class_id)))
    if 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)
