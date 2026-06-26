from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models import Camera
from app.services.camera_service import mask_stream_url


@dataclass(frozen=True)
class RealtimePreviewBatch:
    frames: list[dict[str, Any]]
    events: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class RealtimePreviewWorker:
    def build_preview(self, camera: Camera) -> RealtimePreviewBatch:
        source_type = camera.source_type or "mock"
        if source_type == "file":
            return self._build_file_preview(camera)
        if source_type == "rtsp":
            return self._build_rtsp_preview(camera)
        if source_type == "upload":
            return self._build_upload_preview(camera)
        return self._build_mock_preview(camera)

    def _build_mock_preview(self, camera: Camera) -> RealtimePreviewBatch:
        frames = [
            _frame(camera, index, "mock_frame", "mock stream preview frame")
            for index in range(3)
        ]
        return RealtimePreviewBatch(
            frames=frames,
            events=[
                _event(
                    camera,
                    event_type="realtime_preview_motion",
                    severity="low",
                    frame_index=frames[-1]["frame_index"],
                    description="Deterministic mock motion event for realtime preview.",
                )
            ],
            alerts=[
                _alert(
                    camera,
                    level="info",
                    event_type="realtime_preview_motion",
                    message="Mock realtime preview alert generated.",
                )
            ],
        )

    def _build_file_preview(self, camera: Camera) -> RealtimePreviewBatch:
        path = Path(camera.stream_url or "")
        file_exists = path.exists() if camera.stream_url else False
        status = "file_preview_available" if file_exists else "file_preview_source_missing"
        frames = [
            _frame(
                camera,
                0,
                status,
                "Local file preview smoke metadata.",
                source_label=path.name if camera.stream_url else None,
            )
        ]
        return RealtimePreviewBatch(
            frames=frames,
            events=[
                _event(
                    camera,
                    event_type="local_file_preview",
                    severity="low",
                    frame_index=0,
                    description=status,
                )
            ],
            alerts=[
                _alert(
                    camera,
                    level="info",
                    event_type="local_file_preview",
                    message=status,
                )
            ],
        )

    def _build_rtsp_preview(self, camera: Camera) -> RealtimePreviewBatch:
        frames = [
            _frame(
                camera,
                0,
                "rtsp_preview_not_connected",
                "RTSP preview does not open a network connection in Stage 7AB.",
            )
        ]
        return RealtimePreviewBatch(
            frames=frames,
            events=[
                _event(
                    camera,
                    event_type="rtsp_preview_configured",
                    severity="low",
                    frame_index=0,
                    description="RTSP camera accepted without real RTSP dependency.",
                )
            ],
            alerts=[
                _alert(
                    camera,
                    level="info",
                    event_type="rtsp_preview_configured",
                    message="RTSP preview configured; production streaming is out of scope.",
                )
            ],
        )

    def _build_upload_preview(self, camera: Camera) -> RealtimePreviewBatch:
        frames = [
            _frame(
                camera,
                0,
                "upload_preview_placeholder",
                "Upload-backed realtime preview placeholder.",
            )
        ]
        return RealtimePreviewBatch(
            frames=frames,
            events=[],
            alerts=[],
        )


def _frame(
    camera: Camera,
    frame_index: int,
    status: str,
    description: str,
    *,
    source_label: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "id": f"frame_{uuid4().hex[:12]}",
        "camera_id": camera.id,
        "frame_index": frame_index,
        "timestamp_ms": frame_index * 1000.0,
        "source_type": camera.source_type,
        "source_label": source_label or mask_stream_url(camera.stream_url, camera.source_type),
        "width": camera.width,
        "height": camera.height,
        "fps": camera.fps,
        "status": status,
        "description": description,
        "created_at": now,
    }


def _event(
    camera: Camera,
    *,
    event_type: str,
    severity: str,
    frame_index: int,
    description: str,
) -> dict[str, Any]:
    evidence_id = f"evidence_{uuid4().hex[:12]}"
    return {
        "id": f"event_{uuid4().hex[:12]}",
        "camera_id": camera.id,
        "event_type": event_type,
        "severity": severity,
        "status": "preview",
        "frame_index": frame_index,
        "description": description,
        "evidence": {
            "id": evidence_id,
            "type": "preview_frame_metadata",
            "frame_index": frame_index,
        },
        "created_at": _now_iso(),
    }


def _alert(
    camera: Camera,
    *,
    level: str,
    event_type: str,
    message: str,
) -> dict[str, Any]:
    return {
        "id": f"alert_{uuid4().hex[:12]}",
        "camera_id": camera.id,
        "level": level,
        "status": "preview",
        "event_type": event_type,
        "message": message,
        "created_at": _now_iso(),
    }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
