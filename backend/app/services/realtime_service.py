from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Camera
from app.core.identity import Actor, actor_context
from app.realtime.cache import realtime_preview_cache
from app.realtime.worker import RealtimePreviewWorker
from app.repositories import ProcessingTaskRepository, VideoRepository
from app.services.camera_service import CameraService, camera_to_record


REALTIME_PROCESS_MODE = "realtime_process"


class RealtimePreviewService:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._worker = RealtimePreviewWorker()

    def start(self, camera_id: str, db: Session, *, actor: Actor | None = None) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        if not camera.enabled:
            raise ValueError("disabled camera cannot start realtime preview")

        now = _utc_now()
        video = VideoRepository(db).create(
            id=f"rt_video_{uuid4().hex[:16]}",
            camera_id=camera.id,
            filename=f"{camera.name}-realtime-preview",
            storage_path=f"realtime://camera/{camera.id}",
            status="processing",
            fps=camera.fps,
            width=camera.width,
            height=camera.height,
            frame_count=0,
            duration_seconds=0.0,
            metadata_json={
                "process_mode": "realtime",
                "source_type": camera.source_type,
                "preview": True,
            },
        )
        task = ProcessingTaskRepository(db).create(
            id=f"rt_task_{uuid4().hex[:16]}",
            video_id=video.id,
            status="running",
            mode=REALTIME_PROCESS_MODE,
            parameters={
                "task_type": REALTIME_PROCESS_MODE,
                "camera_id": camera.id,
                "source_type": camera.source_type,
                "preview": True,
                **(actor_context(actor) if actor else {}),
            },
            progress=0.1,
            started_at=now,
        )

        batch = self._worker.build_preview(camera)
        realtime_preview_cache.replace(
            camera.id,
            frames=batch.frames,
            events=batch.events,
            alerts=batch.alerts,
        )

        state = {
            "camera_id": camera.id,
            "status": "running",
            "task_id": task.id,
            "task_type": REALTIME_PROCESS_MODE,
            "video_id": video.id,
            "source_type": camera.source_type,
            "started_at": _to_iso(now),
            "stopped_at": None,
            "frame_count": len(batch.frames),
            "event_count": len(batch.events),
            "alert_count": len(batch.alerts),
            "camera": camera_to_record(camera),
            **(actor_context(actor) if actor else {}),
        }
        self._states[camera.id] = state
        return dict(state)

    def stop(self, camera_id: str, db: Session, *, actor: Actor | None = None) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        previous = self._states.get(camera.id)
        stopped_at = _utc_now()
        if previous and previous.get("status") == "running":
            task_id = previous.get("task_id")
            video_id = previous.get("video_id")
            if task_id:
                ProcessingTaskRepository(db).update_status(
                    str(task_id),
                    "completed",
                    progress=1.0,
                    result={
                        "task_type": REALTIME_PROCESS_MODE,
                        "camera_id": camera.id,
                        "frame_count": previous.get("frame_count", 0),
                        "event_count": previous.get("event_count", 0),
                        "alert_count": previous.get("alert_count", 0),
                        **(actor_context(actor) if actor else {}),
                    },
                    finished_at=stopped_at,
                )
            if video_id:
                VideoRepository(db).update(str(video_id), status="completed")
            state = {
                **previous,
                "status": "stopped",
                "stopped_at": _to_iso(stopped_at),
                "camera": camera_to_record(camera),
            }
        else:
            state = self._idle_state(camera, status="stopped")
        self._states[camera.id] = state
        return dict(state)

    def status(self, camera_id: str, db: Session) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        state = self._states.get(camera.id)
        if state is None:
            return self._idle_state(camera, status="stopped")
        return {**state, "camera": camera_to_record(camera)}

    def recent_frames(self, camera_id: str, db: Session) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        return {
            "camera_id": camera.id,
            "items": realtime_preview_cache.recent_frames(camera.id),
            "total": len(realtime_preview_cache.recent_frames(camera.id)),
            "max_items": realtime_preview_cache.max_items,
        }

    def recent_events(self, camera_id: str, db: Session) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        items = realtime_preview_cache.recent_events(camera.id)
        return {
            "camera_id": camera.id,
            "items": items,
            "total": len(items),
            "max_items": realtime_preview_cache.max_items,
        }

    def recent_alerts(self, camera_id: str, db: Session) -> dict[str, Any]:
        camera = CameraService(db).get_camera_model(camera_id)
        items = realtime_preview_cache.recent_alerts(camera.id)
        return {
            "camera_id": camera.id,
            "items": items,
            "total": len(items),
            "max_items": realtime_preview_cache.max_items,
        }

    def _idle_state(self, camera: Camera, *, status: str) -> dict[str, Any]:
        return {
            "camera_id": camera.id,
            "status": status,
            "task_id": None,
            "task_type": REALTIME_PROCESS_MODE,
            "video_id": None,
            "source_type": camera.source_type,
            "started_at": None,
            "stopped_at": None,
            "frame_count": len(realtime_preview_cache.recent_frames(camera.id)),
            "event_count": len(realtime_preview_cache.recent_events(camera.id)),
            "alert_count": len(realtime_preview_cache.recent_alerts(camera.id)),
            "camera": camera_to_record(camera),
        }


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


realtime_preview_service = RealtimePreviewService()
