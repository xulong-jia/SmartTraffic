from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class VideoRegistry:
    """Small in-memory registry for phase-one video API skeletons."""

    def __init__(self) -> None:
        self._videos: dict[str, dict[str, Any]] = {}

    def create_video(
        self,
        filename: str,
        file_path: str,
        metadata: dict[str, Any],
        process_mode: str = "offline",
    ) -> dict[str, Any]:
        video_id = uuid4().hex
        now = _utc_now_iso()
        record = {
            "id": video_id,
            "filename": filename,
            "file_path": file_path,
            "output_path": None,
            "status": "uploaded",
            "fps": float(metadata.get("fps", 0.0)),
            "width": int(metadata.get("width", 0)),
            "height": int(metadata.get("height", 0)),
            "duration_seconds": float(metadata.get("duration_seconds", 0.0)),
            "total_frames": int(metadata.get("total_frames", 0)),
            "camera_id": metadata.get("camera_id"),
            "process_mode": process_mode,
            "created_at": now,
            "updated_at": now,
        }
        self._videos[video_id] = record
        return dict(record)

    def list_videos(self) -> list[dict[str, Any]]:
        return sorted(self._videos.values(), key=lambda item: item["created_at"])

    def get_video(self, video_id: str) -> dict[str, Any]:
        if video_id not in self._videos:
            raise KeyError(video_id)
        return dict(self._videos[video_id])

    def update_status(self, video_id: str, status: str) -> dict[str, Any]:
        if video_id not in self._videos:
            raise KeyError(video_id)
        self._videos[video_id]["status"] = status
        self._videos[video_id]["updated_at"] = _utc_now_iso()
        return dict(self._videos[video_id])

    def clear(self) -> None:
        self._videos.clear()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


video_registry = VideoRegistry()
