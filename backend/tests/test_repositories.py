from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models as models
from app.repositories import (
    AlertRepository,
    BadCaseRepository,
    DetectionRepository,
    EvaluationDatasetRepository,
    EvaluationResultRepository,
    EventRepository,
    EventRuleRepository,
    FrameRepository,
    ModelRunRepository,
    ProcessingTaskRepository,
    ReviewCommentRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    VideoRepository,
    ZoneRepository,
)


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def seed_video_and_run(session):
    video = VideoRepository(session).create(
        id="video-1",
        filename="demo.mp4",
        storage_path="local_videos/demo.mp4",
        status="uploaded",
    )
    run = TrafficAnalysisRunRepository(session).create(
        id="run-1",
        video_id=video.id,
        status="completed",
        result_dir="results/traffic_analysis/run-1",
        artifact_index={"detections": "detections.jsonl"},
    )
    return video, run


def test_video_and_frame_repository_crud():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        repo = VideoRepository(session)
        video = repo.create(
            id="video-1",
            filename="input.mp4",
            storage_path="local_videos/input.mp4",
            status="uploaded",
        )
        assert repo.get(video.id).filename == "input.mp4"
        assert [item.id for item in repo.list(status="uploaded")] == ["video-1"]

        updated = repo.update(video.id, status="completed")
        assert updated.status == "completed"

        frame = FrameRepository(session).create(
            id="frame-1",
            video_id=video.id,
            frame_index=10,
            timestamp_ms=400.0,
            metadata_json={"source": "test"},
        )
        assert FrameRepository(session).list(video_id=video.id)[0].id == frame.id


def test_processing_task_repository_create_and_status_update():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        video, _ = seed_video_and_run(session)
        repo = ProcessingTaskRepository(session)

        task = repo.create(
            id="task-1",
            video_id=video.id,
            status="queued",
            mode="detection_tracking_trajectory",
            parameters={"dry_run": True},
        )
        assert repo.get(task.id).status == "queued"

        updated = repo.update_status(task.id, "completed", result={"run_id": "run-1"})
        assert updated.status == "completed"
        assert updated.result["run_id"] == "run-1"


def test_traffic_analysis_run_repository_create_get_list():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        video, run = seed_video_and_run(session)
        repo = TrafficAnalysisRunRepository(session)

        assert repo.get(run.id).video_id == video.id
        assert repo.list(video_id=video.id)[0].id == run.id
        assert repo.list(status="completed")[0].id == run.id


def test_detection_tracking_trajectory_repositories_bulk_list_by_run_id():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        video, run = seed_video_and_run(session)

        detections = DetectionRepository(session).bulk_create(
            [
                {
                    "id": "det-1",
                    "run_id": run.id,
                    "video_id": video.id,
                    "frame_index": 1,
                    "class_name": "car",
                    "confidence": 0.91,
                    "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                }
            ]
        )
        tracks = TrackRepository(session).bulk_create(
            [
                {
                    "id": "track-row-1",
                    "run_id": run.id,
                    "video_id": video.id,
                    "track_id": "track-1",
                    "class_name": "car",
                    "start_frame": 1,
                    "end_frame": 3,
                }
            ]
        )
        points = TrajectoryPointRepository(session).bulk_create(
            [
                {
                    "id": "point-1",
                    "run_id": run.id,
                    "video_id": video.id,
                    "track_id": "track-1",
                    "frame_index": 1,
                    "x": 10.0,
                    "y": 20.0,
                    "features": {"speed_px_per_second": 8.5},
                }
            ]
        )

        assert DetectionRepository(session).list(run_id=run.id)[0].id == detections[0].id
        assert TrackRepository(session).list(run_id=run.id)[0].id == tracks[0].id
        assert TrajectoryPointRepository(session).list(run_id=run.id)[0].id == points[0].id


def test_zone_and_event_rule_repositories_crud():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        zone_repo = ZoneRepository(session)
        rule_repo = EventRuleRepository(session)

        zone = zone_repo.create(
            id="zone-1",
            name="Lane A",
            type="polygon",
            coordinates={"points": [[0, 0], [1, 0], [1, 1]]},
            status="active",
        )
        rule = rule_repo.create(
            id="rule-1",
            zone_id=zone.id,
            name="Danger Zone",
            type="danger_zone_intrusion",
            status="enabled",
            parameters={"severity": "high"},
        )

        assert zone_repo.get(zone.id).name == "Lane A"
        assert rule_repo.list(type="danger_zone_intrusion")[0].id == rule.id
        assert rule_repo.update(rule.id, status="disabled").status == "disabled"
        assert zone_repo.delete(zone.id) is True


def test_event_alert_review_bad_case_repositories():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        video, run = seed_video_and_run(session)
        zone = ZoneRepository(session).create(
            id="zone-1",
            name="Lane A",
            type="polygon",
            coordinates={"points": [[0, 0], [1, 0], [1, 1]]},
        )
        rule = EventRuleRepository(session).create(
            id="rule-1",
            zone_id=zone.id,
            name="Wrong Way",
            type="wrong_way_driving",
        )
        event_repo = EventRepository(session)
        event = event_repo.create(
            id="event-1",
            run_id=run.id,
            video_id=video.id,
            rule_id=rule.id,
            zone_id=zone.id,
            type="wrong_way_driving",
            status="new",
            severity="high",
            payload={"track_id": "track-1"},
        )
        assert event_repo.list(run_id=run.id, type="wrong_way_driving")[0].id == event.id
        assert event_repo.update_status(event.id, "reviewed").status == "reviewed"

        alert_repo = AlertRepository(session)
        alert = alert_repo.create(
            id="alert-1",
            run_id=run.id,
            event_id=event.id,
            type="wrong_way_driving",
            status="new",
            severity="high",
            message="Wrong way detected",
        )
        assert alert_repo.list(status="new")[0].id == alert.id
        assert alert_repo.update_status(alert.id, "acknowledged").status == "acknowledged"

        comment = ReviewCommentRepository(session).create(
            id="review-1",
            run_id=run.id,
            event_id=event.id,
            author="tester",
            status="open",
            body="Needs review",
        )
        assert ReviewCommentRepository(session).list(event_id=event.id)[0].id == comment.id

        bad_case_repo = BadCaseRepository(session)
        bad_case = bad_case_repo.create(
            id="bad-1",
            run_id=run.id,
            event_id=event.id,
            type="false_positive",
            status="open",
            severity="medium",
            description="Review mismatch",
            tags=["review"],
        )
        assert bad_case_repo.get(bad_case.id).type == "false_positive"
        assert bad_case_repo.list(status="open", type="false_positive")[0].id == bad_case.id
        assert bad_case_repo.update(bad_case.id, status="closed").status == "closed"


def test_evaluation_and_model_run_repositories():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        _, run = seed_video_and_run(session)
        dataset_repo = EvaluationDatasetRepository(session)
        result_repo = EvaluationResultRepository(session)
        model_run_repo = ModelRunRepository(session)

        dataset = dataset_repo.create(
            id="dataset-1",
            name="Toy Expected Events",
            dataset_type="event",
            version="v1",
            status="active",
            config={"path": "evals/expected/demo_expected_events.json"},
        )
        result = result_repo.create(
            id="eval-result-1",
            dataset_id=dataset.id,
            run_id=run.id,
            evaluation_type="event",
            status="completed",
            metrics={"precision": 1.0},
        )
        model_run = model_run_repo.create(
            id="model-run-1",
            run_id=run.id,
            model_name="yolov8",
            model_version="dry-run",
            task_type="detection",
            metrics={"frames": 3},
        )

        assert dataset_repo.list(status="active")[0].id == dataset.id
        assert result_repo.list(run_id=run.id)[0].id == result.id
        assert result_repo.list(dataset_id=dataset.id)[0].id == result.id
        assert model_run_repo.list(run_id=run.id)[0].id == model_run.id


def test_repository_update_missing_returns_none():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        assert VideoRepository(session).update("missing", status="completed") is None
        assert VideoRepository(session).delete("missing") is False
