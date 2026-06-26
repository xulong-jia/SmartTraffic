from app.analysis.regression_metrics import compute_bad_case_regression


def test_regression_metrics_suggest_fixed_reopened_and_ignore_statuses() -> None:
    details = compute_bad_case_regression(
        [
            {
                "case_id": "case-open-pass",
                "case_type": "false_positive",
                "module": "event_engine",
                "status": "open",
                "expected_result": "no event",
                "actual_result": "event emitted",
                "regression_replay": {"actual_result": "no event"},
            },
            {
                "case_id": "case-fixed-fail",
                "case_type": "false_negative",
                "module": "event_engine",
                "status": "fixed",
                "expected_result": "event emitted",
                "actual_result": "event emitted",
                "regression_replay": {"actual_result": "missing event"},
            },
            {
                "case_id": "case-ignored",
                "case_type": "id_switch",
                "module": "tracker",
                "status": "ignored",
                "expected_result": "stable id",
                "actual_result": "id switch",
                "regression_replay": {"actual_result": "stable id"},
            },
        ],
    )

    assert details["status"] == "available"
    assert details["total_case_count"] == 3
    assert details["evaluated_case_count"] == 2
    assert details["passed_case_count"] == 1
    assert details["failed_case_count"] == 1
    assert details["ignored_case_count"] == 1
    assert details["fixed_case_count"] == 1
    assert details["reopened_case_count"] == 1
    assert details["regression_pass_rate"] == 0.5
    assert details["by_case_type"]["false_positive"]["passed"] == 1
    assert details["by_module"]["event_engine"]["failed"] == 1

    by_id = {result["bad_case_id"]: result for result in details["case_results"]}
    assert by_id["case-open-pass"]["passed"] is True
    assert by_id["case-open-pass"]["fixed"] is True
    assert by_id["case-fixed-fail"]["passed"] is False
    assert by_id["case-fixed-fail"]["reopened"] is True
    assert by_id["case-ignored"]["evaluated"] is False


def test_regression_metrics_do_not_fake_pass_when_replay_data_is_missing() -> None:
    details = compute_bad_case_regression(
        [
            {
                "case_id": "case-no-replay",
                "case_type": "rule_error",
                "module": "event_engine",
                "status": "open",
                "expected_result": "event emitted",
                "actual_result": "missing event",
            }
        ]
    )

    assert details["status"] == "insufficient_data"
    assert details["evaluated_case_count"] == 0
    assert details["passed_case_count"] == 0
    assert details["failed_case_count"] == 0
    assert details["insufficient_data_count"] == 1
    assert details["case_results"][0]["passed"] is None
    assert details["case_results"][0]["reason"] == "insufficient_data"


def test_regression_metrics_can_replay_stored_event_rule_fixture() -> None:
    details = compute_bad_case_regression(
        [
            {
                "case_id": "case-rule-replay",
                "case_type": "rule_error",
                "module": "event_engine",
                "status": "open",
                "expected_result": "flow_counting:1",
                "actual_result": "flow_counting:0",
                "rule_replay": {
                    "run_id": "run-rule",
                    "video_id": "video-rule",
                    "expected_event_count": 1,
                    "event_type": "flow_counting",
                    "rules": [
                        {
                            "rule_id": "rule-flow",
                            "name": "Main line",
                            "event_type": "flow_counting",
                            "parameters": {
                                "line_id": "main",
                                "line": [[5, 0], [5, 10]],
                                "direction": "any",
                                "point_type": "center",
                                "count_once_per_track": True,
                            },
                        }
                    ],
                    "trajectory_frames": [
                        {
                            "frame_index": 1,
                            "timestamp_ms": 100,
                            "trajectory_points": [
                                {
                                    "track_id": 1,
                                    "class_name": "car",
                                    "center": [0, 5],
                                    "bbox": [0, 0, 2, 2],
                                    "track_length": 1,
                                }
                            ],
                        },
                        {
                            "frame_index": 2,
                            "timestamp_ms": 200,
                            "trajectory_points": [
                                {
                                    "track_id": 1,
                                    "class_name": "car",
                                    "center": [10, 5],
                                    "bbox": [8, 4, 12, 6],
                                    "track_length": 2,
                                }
                            ],
                        },
                    ],
                },
            }
        ]
    )

    result = details["case_results"][0]
    assert result["passed"] is True
    assert result["replay_result"]["event_count"] == 1
    assert result["reason"] == "rule_replay_passed"
