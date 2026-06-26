from app.analysis.tracking_metrics import compute_tracking_benchmark


def test_tracking_benchmark_reports_perfect_idf1_mota_and_no_id_switches() -> None:
    details = compute_tracking_benchmark(
        predictions=[
            {"frame_index": 1, "track_id": "p1", "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "track_id": "p1", "class_name": "car", "bbox": [1, 0, 11, 10]},
        ],
        ground_truth=[
            {"frame_index": 1, "gt_track_id": "g1", "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "gt_track_id": "g1", "class_name": "car", "bbox": [1, 0, 11, 10]},
        ],
    )

    assert details["status"] == "available"
    assert details["idf1"] == 1.0
    assert details["mota"] == 1.0
    assert details["id_switch_count"] == 0
    assert details["track_lost_count"] == 0


def test_tracking_benchmark_counts_misses_false_positives_switches_and_lost_segments() -> None:
    details = compute_tracking_benchmark(
        predictions=[
            {"frame_index": 1, "track_id": "p1", "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "track_id": "p2", "class_name": "car", "bbox": [1, 0, 11, 10]},
            {"frame_index": 2, "track_id": "fp", "class_name": "car", "bbox": [50, 50, 60, 60]},
        ],
        ground_truth=[
            {"frame_index": 1, "gt_track_id": "g1", "class_name": "car", "bbox": [0, 0, 10, 10]},
            {"frame_index": 2, "gt_track_id": "g1", "class_name": "car", "bbox": [1, 0, 11, 10]},
            {"frame_index": 3, "gt_track_id": "g1", "class_name": "car", "bbox": [2, 0, 12, 10]},
        ],
    )

    assert details["gt_count"] == 3
    assert details["predicted_count"] == 3
    assert details["idtp"] == 2
    assert details["idfp"] == 1
    assert details["idfn"] == 1
    assert details["idf1"] == 0.666667
    assert details["mota"] == 0.0
    assert details["false_positive_count"] == 1
    assert details["false_negative_count"] == 1
    assert details["id_switch_count"] == 1
    assert details["track_lost_count"] == 1
    assert details["switch_details"][0]["gt_track_id"] == "g1"
    assert details["lost_track_details"][0]["gt_track_id"] == "g1"


def test_tracking_benchmark_handles_missing_ground_truth() -> None:
    details = compute_tracking_benchmark(
        predictions=[{"frame_index": 1, "track_id": "p1", "class_name": "car", "bbox": [0, 0, 10, 10]}],
        ground_truth=[],
    )

    assert details["status"] == "insufficient_data"
    assert details["reason"] == "not_enough_annotations"
