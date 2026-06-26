import pytest

from app.analysis.detection_metrics import bbox_iou, compute_detection_benchmark


def test_bbox_iou_handles_overlap_no_overlap_and_invalid_boxes() -> None:
    assert bbox_iou([0, 0, 10, 10], [5, 5, 15, 15]) == pytest.approx(0.142857, abs=1e-6)
    assert bbox_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert bbox_iou([10, 0, 0, 10], [0, 0, 10, 10]) == 0.0


def test_detection_benchmark_reports_perfect_map_precision_and_recall() -> None:
    details = compute_detection_benchmark(
        predictions=[
            {"frame_index": 1, "class_name": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "class_name": "bus", "confidence": 0.8, "bbox": [20, 20, 30, 30]},
        ],
        ground_truth=[
            {"frame_index": 1, "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "class_name": "bus", "bbox": [20, 20, 30, 30]},
        ],
    )

    assert details["status"] == "available"
    assert details["overall"]["precision"] == 1.0
    assert details["overall"]["recall"] == 1.0
    assert details["overall"]["mAP"] == 1.0
    assert details["per_class"]["car"]["ap"] == 1.0
    assert details["per_class"]["bus"]["ap"] == 1.0


def test_detection_benchmark_counts_false_positive_false_negative_and_class_mismatch() -> None:
    details = compute_detection_benchmark(
        predictions=[
            {"frame_index": 1, "class_name": "car", "confidence": 0.95, "bbox": [0, 0, 10, 10]},
            {"frame_index": 1, "class_name": "car", "confidence": 0.75, "bbox": [40, 40, 50, 50]},
            {"frame_index": 2, "class_name": "car", "confidence": 0.70, "bbox": [20, 20, 30, 30]},
        ],
        ground_truth=[
            {"frame_index": 1, "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "class_name": "bus", "bbox": [20, 20, 30, 30]},
        ],
    )

    assert details["overall"]["true_positive"] == 1
    assert details["overall"]["false_positive"] == 2
    assert details["overall"]["false_negative"] == 1
    assert details["overall"]["precision"] == pytest.approx(0.333333, abs=1e-6)
    assert details["overall"]["recall"] == 0.5
    assert details["overall"]["mAP"] == 0.5
    assert details["per_class"]["bus"]["ap"] == 0.0
    assert len(details["false_positives"]) == 2
    assert len(details["false_negatives"]) == 1


def test_detection_benchmark_handles_missing_ground_truth_and_predictions() -> None:
    no_ground_truth = compute_detection_benchmark(
        predictions=[
            {"frame_index": 1, "class_name": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10]}
        ],
        ground_truth=[],
    )
    no_predictions = compute_detection_benchmark(
        predictions=[],
        ground_truth=[{"frame_index": 1, "class_name": "car", "bbox": [0, 0, 10, 10]}],
    )

    assert no_ground_truth["status"] == "insufficient_data"
    assert no_ground_truth["reason"] == "not_enough_annotations"
    assert no_predictions["status"] == "available"
    assert no_predictions["overall"]["precision"] == 0.0
    assert no_predictions["overall"]["recall"] == 0.0
    assert no_predictions["overall"]["mAP"] == 0.0
