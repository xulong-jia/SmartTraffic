from app.services.video_service import VideoRegistry


def test_video_registry_creates_video_record_from_metadata() -> None:
    registry = VideoRegistry()

    record = registry.create_video(
        filename="road.mp4",
        file_path="/tmp/road.mp4",
        metadata={
            "fps": 25.0,
            "width": 1280,
            "height": 720,
            "duration_seconds": 12.0,
            "total_frames": 300,
        },
    )

    assert record["filename"] == "road.mp4"
    assert record["status"] == "uploaded"
    assert record["fps"] == 25.0
    assert registry.get_video(record["id"]) == record
