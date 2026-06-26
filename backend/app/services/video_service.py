from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Frame, Video
from app.repositories import FrameRepository, VideoRepository


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


class VideoDbService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.videos = VideoRepository(session)
        self.frames = FrameRepository(session)

    def create_video(
        self,
        filename: str,
        file_path: str,
        metadata: dict[str, Any],
        process_mode: str = "offline",
    ) -> dict[str, Any]:
        video = self.videos.create(
            id=uuid4().hex,
            filename=filename,
            storage_path=file_path,
            status="uploaded",
            fps=float(metadata.get("fps", 0.0)),
            width=int(metadata.get("width", 0)),
            height=int(metadata.get("height", 0)),
            duration_seconds=float(metadata.get("duration_seconds", 0.0)),
            frame_count=int(metadata.get("total_frames", 0)),
            camera_id=metadata.get("camera_id"),
            metadata_json={
                **metadata,
                "process_mode": process_mode,
            },
        )
        return video_to_record(video)

    def list_videos(self) -> list[dict[str, Any]]:
        return [video_to_record(video) for video in self.videos.list()]

    def get_video(self, video_id: str) -> dict[str, Any]:
        video = self.videos.get(video_id)
        if video is None:
            raise KeyError(video_id)
        return video_to_record(video)

    def update_status(self, video_id: str, status: str) -> dict[str, Any]:
        video = self.videos.update(video_id, status=status)
        if video is None:
            raise KeyError(video_id)
        return video_to_record(video)

    def list_frames(self, video_id: str) -> list[dict[str, Any]]:
        if self.videos.get(video_id) is None:
            raise KeyError(video_id)
        frames = self.frames.list(video_id=video_id)
        return [frame_to_record(frame) for frame in frames]


def video_to_record(video: Video) -> dict[str, Any]:
    metadata = video.metadata_json or {}
    return {
        "id": video.id,
        "filename": video.filename,
        "file_path": video.storage_path,
        "output_path": metadata.get("output_path"),
        "status": video.status,
        "fps": float(video.fps or 0.0),
        "width": int(video.width or 0),
        "height": int(video.height or 0),
        "duration_seconds": float(video.duration_seconds or 0.0),
        "total_frames": int(video.frame_count or 0),
        "camera_id": video.camera_id,
        "process_mode": str(metadata.get("process_mode") or "offline"),
        "created_at": _to_iso(video.created_at),
        "updated_at": _to_iso(video.updated_at),
    }


def frame_to_record(frame: Frame) -> dict[str, Any]:
    return {
        "id": frame.id,
        "video_id": frame.video_id,
        "frame_index": frame.frame_index,
        "timestamp_ms": frame.timestamp_ms,
        "image_path": frame.image_path,
        "metadata": frame.metadata_json or {},
        "created_at": _to_iso(frame.created_at),
        "updated_at": _to_iso(frame.updated_at),
    }


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)
