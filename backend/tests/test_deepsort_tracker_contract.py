import numpy as np

from app.cv.deepsort_tracker import DeepSortTracker


def test_dry_run_tracker_returns_stable_track_contract() -> None:
    tracker = DeepSortTracker(
        dry_run=True,
        min_confidence=0.5,
        target_classes={"car"},
        max_age=2,
    )
    frame = np.zeros((48, 64, 3), dtype=np.uint8)

    first = tracker.update(
        frame,
        [
            {
                "class_name": "car",
                "class_id": 2,
                "confidence": 0.91,
                "bbox": [10.0, 10.0, 24.0, 24.0],
            },
            {
                "class_name": "person",
                "class_id": 0,
                "confidence": 0.95,
                "bbox": [40.0, 10.0, 52.0, 34.0],
            },
        ],
        frame_index=1,
        timestamp_ms=100,
    )
    second = tracker.update(
        frame,
        [
            {
                "class_name": "car",
                "class_id": 2,
                "confidence": 0.88,
                "bbox": [11.0, 10.0, 25.0, 24.0],
            }
        ],
        frame_index=2,
        timestamp_ms=200,
    )

    assert first["frame_index"] == 1
    assert first["timestamp_ms"] == 100
    assert len(first["tracks"]) == 1
    track = first["tracks"][0]
    assert track["track_id"] > 0
    assert track["class_name"] == "car"
    assert track["class_id"] == 2
    assert track["bbox"] == [10.0, 10.0, 24.0, 24.0]
    assert track["center"] == [17.0, 17.0]
    assert track["state"] == "confirmed"

    assert second["tracks"][0]["track_id"] == track["track_id"]
    assert tracker.is_available()
    assert tracker.get_tracker_info()["dry_run"] is True
