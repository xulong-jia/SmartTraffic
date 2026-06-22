from pathlib import Path

import cv2
import numpy as np

from app.cv.frame_reader import read_video_metadata


def test_read_video_metadata_returns_opencv_video_properties(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for _ in range(5):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    metadata = read_video_metadata(video_path)

    assert metadata["filename"] == "sample.mp4"
    assert metadata["fps"] > 0
    assert metadata["width"] == 64
    assert metadata["height"] == 48
    assert metadata["total_frames"] == 5
    assert metadata["duration_seconds"] > 0
