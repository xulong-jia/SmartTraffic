from app.analysis.evaluation_metrics import (
    compute_detection_metrics,
    compute_event_metrics,
    compute_flow_counting_metrics,
    compute_tracking_metrics,
    compute_trajectory_metrics,
)


def test_event_metrics_match_by_type_and_frame_overlap() -> None:
    metrics = compute_event_metrics(
        expected_events=[
            {"event_id": "expected_1", "event_type": "wrong_way_driving", "start_frame": 10, "end_frame": 20},
            {"event_id": "expected_2", "event_type": "illegal_parking", "start_frame": 40, "end_frame": 50},
        ],
        actual_events=[
            {"event_id": "actual_1", "event_type": "wrong_way_driving", "start_frame": 12, "end_frame": 18},
            {"event_id": "actual_2", "event_type": "danger_zone_intrusion", "start_frame": 60, "end_frame": 70},
        ],
        frame_tolerance=0,
    )

    assert metrics["status"] == "available"
    assert metrics["event_count_expected"] == 2
    assert metrics["event_count_actual"] == 2
    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["failed_cases"][0]["failure_type"] == "false_negative"


def test_event_metrics_without_expected_annotations_is_not_applicable() -> None:
    metrics = compute_event_metrics(expected_events=[], actual_events=[])

    assert metrics["status"] == "not_applicable"
    assert metrics["reason"] == "missing expected events"
    assert metrics["precision"] is None


def test_flow_counting_metrics_compute_aggregate_errors() -> None:
    metrics = compute_flow_counting_metrics(
        expected_counts={
            "summary": {"total_count": 10},
            "by_class": {"car": 7, "bus": 3},
            "by_direction": {"in": 6, "out": 4},
        },
        actual_counts={
            "summary": {"total_count": 8},
            "records": [
                {"class_name": "car", "direction": "in", "count": 5},
                {"class_name": "bus", "direction": "out", "count": 3},
            ],
        },
    )

    assert metrics["status"] == "available"
    assert metrics["expected_total"] == 10
    assert metrics["actual_total"] == 8
    assert metrics["absolute_error"] == 2
    assert metrics["mae"] == 2
    assert metrics["mape"] == 0.2
    assert metrics["by_class_error"] == {"bus": 0, "car": 2}


def test_trajectory_metrics_summarize_points() -> None:
    metrics = compute_trajectory_metrics(
        {
            "frames": [
                {
                    "trajectory_points": [
                        {"track_id": 1, "track_length": 2, "speed_px_per_second": 10, "moving_angle": 90},
                        {"track_id": 1, "track_length": 3, "speed_px_per_second": 20, "moving_angle": None},
                        {"track_id": 2, "track_length": 1, "speed_px_per_second": None, "moving_angle": 180},
                    ]
                }
            ]
        }
    )

    assert metrics["status"] == "available"
    assert metrics["track_count"] == 2
    assert metrics["total_trajectory_points"] == 3
    assert metrics["average_track_length"] == 2
    assert metrics["average_speed"] == 15
    assert metrics["direction_available_count"] == 2


def test_detection_and_tracking_without_annotations_are_not_applicable() -> None:
    assert compute_detection_metrics(None, [])["status"] == "not_applicable"
    assert compute_tracking_metrics(None, [])["status"] == "not_applicable"
