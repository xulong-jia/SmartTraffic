from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Camera
from app.repositories import CameraRepository


SUPPORTED_CAMERA_SOURCE_TYPES = {"upload", "rtsp", "file", "mock"}


class CameraService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cameras = CameraRepository(session)

    def create_camera(self, payload: dict[str, Any]) -> dict[str, Any]:
        values = _clean_camera_values(payload)
        _validate_source_type(values.get("source_type") or "mock")
        camera = self.cameras.create(
            id=uuid4().hex,
            name=values["name"],
            location=values.get("location"),
            source_type=values.get("source_type") or "mock",
            stream_url=values.get("stream_url"),
            enabled=values.get("enabled", True),
            status="active" if values.get("enabled", True) else "disabled",
            width=values.get("width"),
            height=values.get("height"),
            fps=values.get("fps"),
            metadata_json=values.get("metadata") or {},
        )
        return camera_to_record(camera)

    def list_cameras(
        self,
        *,
        source_type: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {"source_type": source_type, "enabled": enabled}
        return [camera_to_record(camera) for camera in self.cameras.list(**filters)]

    def get_camera(self, camera_id: str) -> dict[str, Any]:
        camera = self.get_camera_model(camera_id)
        return camera_to_record(camera)

    def get_camera_model(self, camera_id: str) -> Camera:
        camera = self.cameras.get(camera_id)
        if camera is None:
            raise KeyError(camera_id)
        return camera

    def update_camera(self, camera_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        values = _clean_camera_values(payload)
        if "source_type" in values and values["source_type"] is not None:
            _validate_source_type(values["source_type"])
        if "metadata" in values:
            values["metadata_json"] = values.pop("metadata") or {}
        if "enabled" in values and values["enabled"] is not None:
            values["status"] = "active" if values["enabled"] else "disabled"
        camera = self.cameras.update(camera_id, **values)
        if camera is None:
            raise KeyError(camera_id)
        return camera_to_record(camera)

    def enable_camera(self, camera_id: str) -> dict[str, Any]:
        camera = self.cameras.update(camera_id, enabled=True, status="active")
        if camera is None:
            raise KeyError(camera_id)
        return camera_to_record(camera)

    def disable_camera(self, camera_id: str) -> dict[str, Any]:
        camera = self.cameras.update(camera_id, enabled=False, status="disabled")
        if camera is None:
            raise KeyError(camera_id)
        return camera_to_record(camera)

    def delete_camera(self, camera_id: str) -> bool:
        return self.cameras.delete(camera_id)


def camera_to_record(camera: Camera) -> dict[str, Any]:
    return {
        "id": camera.id,
        "name": camera.name,
        "location": camera.location,
        "source_type": camera.source_type,
        "masked_stream_url": mask_stream_url(camera.stream_url, camera.source_type),
        "enabled": bool(camera.enabled),
        "status": camera.status,
        "width": camera.width,
        "height": camera.height,
        "fps": camera.fps,
        "metadata": camera.metadata_json or {},
        "created_at": _to_iso(camera.created_at),
        "updated_at": _to_iso(camera.updated_at),
    }


def mask_stream_url(stream_url: str | None, source_type: str | None = None) -> str | None:
    if not stream_url:
        return None
    parsed = urlsplit(stream_url)
    if parsed.scheme in {"rtsp", "http", "https"}:
        host = parsed.hostname or "***"
        port = f":{parsed.port}" if parsed.port else ""
        auth_marker = "***@" if parsed.username or parsed.password else ""
        suffix = "/..." if parsed.path or parsed.query else ""
        return f"{parsed.scheme}://{auth_marker}{host}{port}{suffix}"
    if parsed.scheme == "file":
        return f"file://{Path(parsed.path).name or 'preview-source'}"
    if source_type == "file" or Path(stream_url).is_absolute():
        return Path(stream_url).name or "local-file"
    if len(stream_url) <= 16:
        return "***"
    return f"{stream_url[:6]}...{stream_url[-4:]}"


def _clean_camera_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _validate_source_type(source_type: str) -> None:
    if source_type not in SUPPORTED_CAMERA_SOURCE_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_CAMERA_SOURCE_TYPES))
        raise ValueError(f"source_type must be one of: {allowed}")


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)
