import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.repositories import EvaluationResultRepository, TrafficAnalysisRunRepository, VideoRepository
from app.services.bad_case_service import BadCaseService
from app.services.evaluation_service import EvaluationService


def test_detection_evaluation_writes_benchmark_metrics_to_db(tmp_path: Path) -> None:
    with _session_factory(tmp_path, "detection")() as session:
        _seed_run(session, tmp_path, run_id="run-detection-db")
        _write_jsonl(
            tmp_path / "results" / "run-detection-db" / "detections.jsonl",
            [
                {
                    "frame_index": 1,
                    "detections": [
                        {"class_name": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10]},
                        {"class_name": "car", "confidence": 0.7, "bbox": [40, 40, 50, 50]},
                    ],
                }
            ],
        )
        annotation_path = _write_annotation(
            tmp_path,
            "detection_annotations.json",
            {"detections": [{"frame_index": 1, "class_name": "car", "bbox": [0, 0, 10, 10]}]},
        )
        session.commit()

        service = EvaluationService(results_dir=tmp_path / "results", eval_root=tmp_path / "evals", session=session)
        service.register_dataset(
            {
                "dataset_id": "detection-fixture",
                "name": "Detection Fixture",
                "dataset_type": "detection",
                "annotation_path": str(annotation_path),
            }
        )
        response = service.run_evaluation(
            run_id="run-detection-db",
            dataset_id="detection-fixture",
            evaluation_type="detection",
        )
        session.commit()

        metric_names = {result["metric_name"] for result in response["results"]}
        assert {"detection_mAP", "detection_precision", "detection_recall", "detection_ap_car"} <= metric_names
        assert response["results"][0]["details"]["status"] == "available"
        rows = EvaluationResultRepository(session).list(run_id="run-detection-db", evaluation_type="detection")
        stored_names = {row.metrics["metric_name"] for row in rows}
        assert {"detection_mAP", "detection_precision", "detection_recall", "detection_ap_car"} <= stored_names


def test_tracking_evaluation_writes_benchmark_metrics_to_db(tmp_path: Path) -> None:
    with _session_factory(tmp_path, "tracking")() as session:
        _seed_run(session, tmp_path, run_id="run-tracking-db")
        _write_jsonl(
            tmp_path / "results" / "run-tracking-db" / "tracks.jsonl",
            [
                {
                    "frame_index": 1,
                    "tracks": [
                        {"track_id": "p1", "class_name": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10], "center": [5, 5]}
                    ],
                },
                {
                    "frame_index": 2,
                    "tracks": [
                        {"track_id": "p2", "class_name": "car", "confidence": 0.9, "bbox": [1, 0, 11, 10], "center": [6, 5]}
                    ],
                },
            ],
        )
        annotation_path = _write_annotation(
            tmp_path,
            "tracking_annotations.json",
            {
                "tracks": [
                    {"frame_index": 1, "gt_track_id": "g1", "class_name": "car", "bbox": [0, 0, 10, 10]},
                    {"frame_index": 2, "gt_track_id": "g1", "class_name": "car", "bbox": [1, 0, 11, 10]},
                    {"frame_index": 3, "gt_track_id": "g1", "class_name": "car", "bbox": [2, 0, 12, 10]},
                ]
            },
        )
        session.commit()

        service = EvaluationService(results_dir=tmp_path / "results", eval_root=tmp_path / "evals", session=session)
        service.register_dataset(
            {
                "dataset_id": "tracking-fixture",
                "name": "Tracking Fixture",
                "dataset_type": "tracking",
                "annotation_path": str(annotation_path),
            }
        )
        response = service.run_evaluation(
            run_id="run-tracking-db",
            dataset_id="tracking-fixture",
            evaluation_type="tracking",
        )
        session.commit()

        metric_names = {result["metric_name"] for result in response["results"]}
        assert {"tracking_idf1", "tracking_mota", "tracking_id_switches", "tracking_track_lost"} <= metric_names
        assert response["results"][0]["details"]["id_switch_count"] == 1
        assert response["results"][0]["details"]["track_lost_count"] == 1
        failed_case_types = {item["failure_type"] for item in response["failed_cases"]}
        assert {"id_switch", "track_lost"} <= failed_case_types
        id_switch_failed_case = next(
            item
            for item in response["failed_cases"]
            if item["failure_type"] == "id_switch"
        )
        bad_case_service = BadCaseService(eval_root=tmp_path / "evals", session=session)
        bad_case = bad_case_service.create_bad_case_from_failed_case(
            run_id="run-tracking-db",
            failed_case_id=id_switch_failed_case["failed_case_id"],
        )
        assert bad_case["case_type"] == "id_switch"
        assert bad_case["module"] == "tracker"
        assert bad_case["linked_failed_case_id"] == id_switch_failed_case["failed_case_id"]
        assert bad_case_service.list_bad_cases(
            run_id="run-tracking-db",
            case_type="id_switch",
            module="tracker",
        )
        rows = EvaluationResultRepository(session).list(run_id="run-tracking-db", evaluation_type="tracking")
        stored_names = {row.metrics["metric_name"] for row in rows}
        assert {"tracking_idf1", "tracking_mota", "tracking_id_switches", "tracking_track_lost"} <= stored_names


def test_detection_evaluation_without_annotations_returns_insufficient_data(tmp_path: Path) -> None:
    with _session_factory(tmp_path, "missing")() as session:
        _seed_run(session, tmp_path, run_id="run-no-annotation-db")
        session.commit()

        service = EvaluationService(results_dir=tmp_path / "results", eval_root=tmp_path / "evals", session=session)
        response = service.run_evaluation(run_id="run-no-annotation-db", evaluation_type="detection")

        assert response["results"][0]["metric_name"] == "detection_status"
        assert response["results"][0]["details"]["status"] == "insufficient_data"
        assert response["results"][0]["details"]["reason"] == "not_enough_annotations"


def _session_factory(tmp_path: Path, name: str) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / f'{name}.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def _seed_run(session: Session, tmp_path: Path, *, run_id: str) -> None:
    run_dir = tmp_path / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    VideoRepository(session).create(
        id=f"video-{run_id}",
        filename=f"{run_id}.mp4",
        storage_path=f"local_videos/{run_id}.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id=run_id,
        video_id=f"video-{run_id}",
        status="completed",
        result_dir=str(run_dir),
        artifact_index={},
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_annotation(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / "evals" / "expected" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path
