import numpy as np

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
