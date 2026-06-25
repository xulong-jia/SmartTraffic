import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.evaluation_artifacts import (
    append_failed_case,
    append_evaluation_result,
    append_evaluation_run,
    load_evaluation_datasets,
    load_evaluation_runs,
    load_evaluation_results,
    load_failed_cases,
    load_evaluation_summary,
    register_evaluation_dataset,
)
from app.services.evaluation_service import EvaluationService


def test_missing_evaluation_artifacts_return_empty_structures(tmp_path: Path) -> None:
    assert load_evaluation_datasets(tmp_path) == {
        "schema_version": "stage8efg.v1",
        "datasets": [],
    }
    assert load_evaluation_runs(tmp_path) == []
    assert load_evaluation_results(tmp_path) == []
    assert load_failed_cases(tmp_path) == []
    assert load_evaluation_summary(tmp_path / "run_1") == {
        "schema_version": "stage8efg.v1",
        "run_id": "run_1",
        "generated_at": None,
        "summary": {},
        "failed_cases": [],
    }


def test_register_dataset_and_append_evaluation_artifacts(tmp_path: Path) -> None:
    dataset = register_evaluation_dataset(
        tmp_path,
        {
            "dataset_id": "dataset_toy",
            "name": "Toy Event Dataset",
            "dataset_type": "event",
            "expected_events_path": "expected/events.json",
        },
    )
    run = append_evaluation_run(
        tmp_path,
        {
            "evaluation_run_id": "eval_run_1",
            "dataset_id": "dataset_toy",
            "run_id": "run_1",
            "evaluation_type": "event",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
            "config": {},
        },
    )
    result = append_evaluation_result(
        tmp_path,
        {
            "evaluation_result_id": "eval_result_1",
            "evaluation_run_id": "eval_run_1",
            "run_id": "run_1",
            "dataset_id": "dataset_toy",
            "evaluation_type": "event",
            "metric_name": "event_precision",
            "metric_value": 1.0,
            "details": {"status": "available"},
            "created_at": "2026-01-01T00:00:01+00:00",
        },
    )
    failed = append_failed_case(
        tmp_path,
        {
            "failed_case_id": "fail_1",
            "evaluation_run_id": "eval_run_1",
            "run_id": "run_1",
            "failure_type": "false_negative",
            "module": "event_engine",
            "expected": {"event_type": "wrong_way_driving"},
            "actual": {},
            "created_at": "2026-01-01T00:00:01+00:00",
        },
    )

    assert dataset["dataset_id"] == "dataset_toy"
    assert load_evaluation_datasets(tmp_path)["datasets"][0]["dataset_id"] == "dataset_toy"
    assert load_evaluation_runs(tmp_path) == [run]
    assert load_evaluation_results(tmp_path) == [result]
    assert load_failed_cases(tmp_path) == [failed]


def test_evaluation_service_runs_event_flow_trajectory_and_placeholder_metrics(
    tmp_path: Path,
) -> None:
    run_id = _create_evaluation_run(tmp_path)
    eval_root = tmp_path / "evals"
    expected_events = eval_root / "expected" / "events.json"
    expected_events.parent.mkdir(parents=True)
    expected_events.write_text(
        json.dumps(
            {
                "events": [
                    {"event_id": "expected_1", "event_type": "wrong_way_driving", "start_frame": 10, "end_frame": 20},
                    {"event_id": "expected_2", "event_type": "illegal_parking", "start_frame": 40, "end_frame": 50},
                ]
            }
        ),
        encoding="utf-8",
    )
    expected_counts = eval_root / "expected" / "counts.json"
    expected_counts.write_text(
        json.dumps({"summary": {"total_count": 1}, "by_class": {"car": 1}}),
        encoding="utf-8",
    )
    service = EvaluationService(results_dir=tmp_path / "results", eval_root=eval_root)
    service.register_dataset(
        {
            "dataset_id": "dataset_toy",
            "name": "Toy Dataset",
            "dataset_type": "event",
            "expected_events_path": "expected/events.json",
            "expected_counts_path": "expected/counts.json",
        }
    )

    event_response = service.run_evaluation(
        run_id=run_id,
        dataset_id="dataset_toy",
        evaluation_type="event",
    )
    flow_response = service.run_evaluation(
        run_id=run_id,
        dataset_id="dataset_toy",
        evaluation_type="flow_counting",
    )
    trajectory_response = service.run_evaluation(
        run_id=run_id,
        dataset_id="dataset_toy",
        evaluation_type="trajectory",
    )
    detection_response = service.run_evaluation(
        run_id=run_id,
        dataset_id="dataset_toy",
        evaluation_type="detection",
    )

    assert event_response["summary"]["summary"]["event"]["event_precision"]["metric_value"] == 0.5
    assert flow_response["summary"]["summary"]["flow_counting"]["flow_mae"]["metric_value"] == 0
    assert trajectory_response["summary"]["summary"]["trajectory"]["trajectory_track_count"]["metric_value"] == 1
    assert detection_response["summary"]["summary"]["detection"]["detection_status"]["details"]["status"] == "not_applicable"
    assert service.list_results(run_id=run_id)
    assert service.list_failed_cases(run_id=run_id)
    assert service.get_evaluation_summary(run_id)["summary"]["bad_case_regression"]["status"] == "planned"


def _create_evaluation_run(tmp_path: Path) -> str:
    run_id = "run_stage8efg"
    writer = TrafficArtifactWriter(tmp_path / "results")
    writer.create_run_directory(run_id, {"video_id": "video_001", "status": "completed"})
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            {"event_id": "actual_1", "run_id": run_id, "video_id": "video_001", "event_type": "wrong_way_driving", "start_frame": 12, "end_frame": 18, "track_id": 1},
            {"event_id": "actual_2", "run_id": run_id, "video_id": "video_001", "event_type": "flow_counting", "start_frame": 60, "end_frame": 70, "track_id": 1, "class_name": "car"},
        ],
        event_evidence=[],
        rule_executions=[],
    )
    writer.write_trajectory_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 1,
                "timestamp_ms": 100,
                "trajectory_points": [
                    {
                        "track_id": 1,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.9,
                        "bbox": [0, 0, 10, 10],
                        "center": [5, 5],
                        "bottom_center": [5, 10],
                        "state": "confirmed",
                        "track_length": 2,
                        "speed_px_per_second": 10,
                        "moving_angle": 90,
                    }
                ],
            }
        ],
    )
    writer.write_statistics_outputs(run_id)
    return run_id
