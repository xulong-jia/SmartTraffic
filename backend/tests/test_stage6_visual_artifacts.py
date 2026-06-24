import json
from pathlib import Path

import pytest

from app.analysis.artifact_writer import TrafficArtifactWriter


def test_stage6_visual_artifacts_write_empty_keyframe_index_without_events(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = "run_stage6f_empty"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "status": "completed",
            "mode": "offline",
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[],
        event_evidence=[],
        rule_executions=[],
    )
    writer.write_alert_outputs(run_id=run_id, video_id="video_001", alerts=[])

    manifest = writer.write_visual_artifacts(run_id)

    keyframe_index = _read_json(tmp_path / run_id / "keyframes" / "index.json")
    metadata = _read_json(tmp_path / run_id / "metadata.json")
    artifact_index = _read_json(tmp_path / run_id / "artifact_index.json")

    assert keyframe_index["schema_version"] == "stage6f.v1"
    assert keyframe_index["run_id"] == run_id
    assert keyframe_index["video_id"] == "video_001"
    assert keyframe_index["items"] == []
    assert keyframe_index["status"] == "empty"
    assert manifest["artifacts"]["keyframes"]["status"] == "empty"
    assert manifest["artifacts"]["keyframes"]["record_count"] == 0
    assert manifest["artifacts"]["keyframes_index"]["status"] == "available"
    assert manifest["artifacts"]["annotated_video"]["status"] == "missing_source_video"
    assert artifact_index["artifacts"]["keyframes"] == "keyframes/"
    assert artifact_index["artifacts"]["keyframes_index"] == "keyframes/index.json"
    assert artifact_index["artifacts"]["annotated_video"] == "annotated_video.mp4"
    assert metadata["artifact_summary"]["keyframes"]["status"] == "empty"
    assert metadata["artifact_summary"]["keyframes_index"]["status"] == "available"
    assert metadata["artifact_summary"]["annotated_video"]["status"] == "missing_source_video"


def test_stage6_visual_artifacts_mark_keyframe_missing_source_video(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = "run_stage6f_missing_video"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "status": "completed",
            "mode": "offline",
            "input_video": "missing_source.mp4",
        },
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            {
                "event_id": "event_missing_source",
                "event_type": "wrong_way_driving",
                "track_id": 7,
                "start_frame": 1,
                "end_frame": 1,
                "start_time_ms": 100,
                "end_time_ms": 100,
                "severity": "warning",
                "status": "new",
            }
        ],
        event_evidence=[],
        rule_executions=[],
    )
    writer.write_alert_outputs(run_id=run_id, video_id="video_001", alerts=[])

    manifest = writer.write_visual_artifacts(run_id)

    keyframe_index = _read_json(tmp_path / run_id / "keyframes" / "index.json")
    items = keyframe_index["items"]
    assert len(items) == 1
    assert items[0]["source_type"] == "event"
    assert items[0]["source_id"] == "event_missing_source"
    assert items[0]["frame_index"] == 1
    assert items[0]["status"] == "missing_source_video"
    assert not (tmp_path / run_id / items[0]["path"]).is_file()
    assert manifest["artifacts"]["keyframes"]["status"] == "missing_source_video"
    assert manifest["artifacts"]["keyframes"]["record_count"] == 1
    assert manifest["artifacts"]["annotated_video"]["status"] == "missing_source_video"


def test_stage6_visual_artifacts_mark_error_when_event_artifact_is_corrupt(
    tmp_path: Path,
) -> None:
    writer = TrafficArtifactWriter(tmp_path)
    run_id = "run_stage6f_corrupt_events"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "status": "completed",
            "mode": "offline",
        },
    )
    (tmp_path / run_id / "events.jsonl").write_text("{not-json\n", encoding="utf-8")

    manifest = writer.write_visual_artifacts(run_id)

    keyframe_index = _read_json(tmp_path / run_id / "keyframes" / "index.json")
    assert keyframe_index["status"] == "error"
    assert keyframe_index["items"] == []
    assert manifest["artifacts"]["keyframes"]["status"] == "error"
    assert manifest["artifacts"]["keyframes_index"]["status"] == "available"
    assert manifest["artifacts"]["annotated_video"]["status"] == "missing_source_video"


def test_stage6_visual_artifacts_generate_keyframe_and_annotated_video(
    tmp_path: Path,
) -> None:
    cv2 = pytest.importorskip("cv2")
    numpy = pytest.importorskip("numpy")
    video_path = tmp_path / "source.mp4"
    _write_synthetic_video(video_path, cv2=cv2, numpy=numpy)

    writer = TrafficArtifactWriter(tmp_path)
    run_id = "run_stage6f_visual"
    writer.create_run_directory(
        run_id,
        {
            "video_id": "video_001",
            "status": "completed",
            "mode": "offline",
            "input_video": str(video_path),
            "video_metadata": {
                "video_path": str(video_path),
                "fps": 5.0,
                "width": 64,
                "height": 48,
                "total_frames": 3,
            },
        },
    )
    writer.write_detection_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 1,
                "timestamp_ms": 200,
                "detections": [
                    {
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.93,
                        "bbox": [8, 8, 36, 34],
                    }
                ],
            }
        ],
    )
    writer.write_tracking_outputs(
        run_id=run_id,
        video_id="video_001",
        frame_results=[
            {
                "frame_index": 1,
                "timestamp_ms": 200,
                "tracks": [
                    {
                        "track_id": 11,
                        "class_id": 2,
                        "class_name": "car",
                        "confidence": 0.93,
                        "bbox": [8, 8, 36, 34],
                        "center": [22, 21],
                        "state": "confirmed",
                    }
                ],
            }
        ],
    )
    writer.write_event_outputs(
        run_id=run_id,
        video_id="video_001",
        events=[
            {
                "event_id": "event/unsafe:id",
                "event_type": "wrong_way_driving",
                "track_id": 11,
                "start_frame": 1,
                "end_frame": 1,
                "start_time_ms": 200,
                "end_time_ms": 200,
                "severity": "warning",
                "status": "new",
            }
        ],
        event_evidence=[
            {
                "evidence_id": "evidence_event_1",
                "event_id": "event/unsafe:id",
                "event_type": "wrong_way_driving",
                "evidence_type": "trajectory_window",
                "frame_index": 1,
                "timestamp_ms": 200,
            }
        ],
        rule_executions=[],
    )
    writer.write_alert_outputs(
        run_id=run_id,
        video_id="video_001",
        alerts=[
            {
                "alert_id": "alert_1",
                "event_id": "event/unsafe:id",
                "run_id": run_id,
                "video_id": "video_001",
                "alert_type": "traffic_event",
                "title": "Wrong way",
                "message": "Wrong way event",
                "level": "warning",
                "status": "new",
                "frame_index": 1,
                "timestamp_ms": 200,
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )

    manifest = writer.write_visual_artifacts(run_id)

    keyframe_index = _read_json(tmp_path / run_id / "keyframes" / "index.json")
    items = keyframe_index["items"]
    assert len(items) == 2
    assert {item["source_type"] for item in items} == {"event", "alert"}
    assert all(item["status"] == "available" for item in items)
    assert all(".." not in item["path"] for item in items)
    assert all("/" not in Path(item["path"]).name.replace("keyframes/", "") for item in items)
    assert all((tmp_path / run_id / item["path"]).is_file() for item in items)
    assert (tmp_path / run_id / "annotated_video.mp4").is_file()
    assert manifest["artifacts"]["keyframes"]["status"] == "available"
    assert manifest["artifacts"]["keyframes"]["record_count"] == 2
    assert manifest["artifacts"]["keyframes_index"]["status"] == "available"
    assert manifest["artifacts"]["annotated_video"]["status"] == "available"
    assert manifest["artifacts"]["evaluation_summary"]["status"] == "planned"


def _write_synthetic_video(video_path: Path, *, cv2, numpy) -> None:
    video_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        5.0,
        (64, 48),
    )
    assert writer.isOpened()
    try:
        for index in range(3):
            frame = numpy.zeros((48, 64, 3), dtype=numpy.uint8)
            frame[:, :, 0] = 30 * index
            frame[:, :, 1] = 80
            frame[:, :, 2] = 120
            writer.write(frame)
    finally:
        writer.release()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
