import numpy as np
import pytest

from app.cv.yolo_detector import YoloDetector


def test_yolo_detector_dry_run_returns_stable_detection_contract() -> None:
    detector = YoloDetector(model_path="", dry_run=True)
    frame = np.zeros((80, 120, 3), dtype=np.uint8)

    result = detector.detect_frame(frame, frame_index=7, timestamp_ms=233)

    assert result["frame_index"] == 7
    assert result["timestamp_ms"] == 233
    assert result["detections"] == []


def test_yolo_detector_formats_model_results_into_contract() -> None:
    raw_result = {
        "class_id": 2,
        "class_name": "car",
        "confidence": 0.81234,
        "bbox": [1, 2, 30, 40],
    }

    detection = YoloDetector.format_detection(raw_result)

    assert detection == {
        "class_id": 2,
        "class_name": "car",
        "confidence": 0.81234,
        "bbox": [1.0, 2.0, 30.0, 40.0],
    }


def test_yolo_detector_reports_availability_without_loading_missing_model() -> None:
    detector = YoloDetector(model_path="missing.pt", dry_run=False)

    assert detector.is_available() is False
    assert detector.get_model_info() == {
        "model_path": "missing.pt",
        "device": "cpu",
        "image_size": 640,
        "conf_threshold": 0.25,
        "iou_threshold": 0.45,
        "dry_run": False,
        "available": False,
        "loaded": False,
    }


def test_yolo_detector_missing_model_error_is_clear() -> None:
    detector = YoloDetector(model_path="missing.pt", dry_run=False)
    frame = np.zeros((80, 120, 3), dtype=np.uint8)

    with pytest.raises(FileNotFoundError, match="YOLO model not found"):
        detector.detect_frame(frame, frame_index=1)
