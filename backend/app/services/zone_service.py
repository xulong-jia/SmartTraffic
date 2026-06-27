from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories import ZoneRepository
from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate


class ZoneService:
    def __init__(self) -> None:
        self._zones: dict[str, dict[str, Any]] = {}

    def create_zone(self, payload: ZoneCreate | Mapping[str, Any]) -> dict[str, Any]:
        values = _dump_payload(payload)
        zone_id = str(values.get("id") or f"zone_{uuid4().hex[:12]}")
        if zone_id in self._zones:
            raise ValueError(f"zone already exists: {zone_id}")
        values["id"] = zone_id
        zone = ZoneResponse(**values).model_dump()
        self._zones[zone_id] = zone
        return dict(zone)

    def list_zones(
        self,
        *,
        video_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        zones = []
        for zone in self._zones.values():
            if video_id is not None and zone.get("video_id") not in {video_id, None}:
                continue
            if enabled is not None and bool(zone.get("enabled", True)) is not enabled:
                continue
            zones.append(dict(zone))
        return zones

    def get_zone(self, zone_id: str) -> dict[str, Any]:
        if zone_id not in self._zones:
            raise KeyError(zone_id)
        return dict(self._zones[zone_id])

    def update_zone(
        self,
        zone_id: str,
        payload: ZoneUpdate | Mapping[str, Any],
    ) -> dict[str, Any]:
        current = self.get_zone(zone_id)
        updates = _dump_payload(payload, exclude_unset=True)
        updates.pop("id", None)
        current.update(updates)
        current["id"] = zone_id
        zone = ZoneResponse(**current).model_dump()
        self._zones[zone_id] = zone
        return dict(zone)

    def delete_zone(self, zone_id: str) -> None:
        if zone_id not in self._zones:
            raise KeyError(zone_id)
        del self._zones[zone_id]

    def build_event_engine_zones(
        self,
        *,
        video_id: str | None = None,
        camera_id: str | None = None,
        zones: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        del camera_id
        source_zones = (
            [dict(zone) for zone in zones]
            if zones is not None
            else self.list_zones(video_id=video_id, enabled=True)
        )
        return [_to_event_engine_zone(zone) for zone in source_zones]

    def clear(self) -> None:
        self._zones.clear()


def _to_event_engine_zone(zone: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(zone)
    zone_id = normalized.get("zone_id") or normalized.get("id")
    normalized["id"] = str(normalized.get("id") or zone_id)
    normalized["zone_id"] = str(zone_id)
    return normalized


def _dump_payload(
    payload: ZoneCreate | ZoneUpdate | Mapping[str, Any],
    *,
    exclude_unset: bool = False,
) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_none=True, exclude_unset=exclude_unset)
    return {key: value for key, value in dict(payload).items() if value is not None}


zone_service = ZoneService()


class ZoneDbService:
    def __init__(self, session: Session) -> None:
        self.repo = ZoneRepository(session)

    def create_zone(self, payload: ZoneCreate | Mapping[str, Any]) -> dict[str, Any]:
        values = _dump_payload(payload)
        zone_id = str(values.get("id") or f"zone_{uuid4().hex[:12]}")
        if self.repo.get(zone_id) is not None:
            raise ValueError(f"zone already exists: {zone_id}")
        zone = ZoneResponse(**{**values, "id": zone_id}).model_dump()
        row = self.repo.create(**_zone_to_model_values(zone))
        return _zone_from_model(row)

    def list_zones(
        self,
        *,
        video_id: str | None = None,
        camera_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        zones = []
        for row in self.repo.list():
            zone = _zone_from_model(row)
            if video_id is not None and zone.get("video_id") not in {video_id, None}:
                continue
            if camera_id is not None and zone.get("camera_id") not in {camera_id, None}:
                continue
            if enabled is not None and bool(zone.get("enabled", True)) is not enabled:
                continue
            zones.append(zone)
        return zones

    def get_zone(self, zone_id: str) -> dict[str, Any]:
        row = self.repo.get(zone_id)
        if row is None:
            raise KeyError(zone_id)
        return _zone_from_model(row)

    def update_zone(
        self,
        zone_id: str,
        payload: ZoneUpdate | Mapping[str, Any],
    ) -> dict[str, Any]:
        current = self.get_zone(zone_id)
        updates = _dump_payload(payload, exclude_unset=True)
        updates.pop("id", None)
        zone = ZoneResponse(**{**current, **updates, "id": zone_id}).model_dump()
        row = self.repo.update(zone_id, **_zone_to_model_values(zone, include_id=False))
        if row is None:
            raise KeyError(zone_id)
        return _zone_from_model(row)

    def delete_zone(self, zone_id: str) -> None:
        if not self.repo.delete(zone_id):
            raise KeyError(zone_id)

    def build_event_engine_zones(
        self,
        *,
        video_id: str | None = None,
        camera_id: str | None = None,
        zones: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        source_zones = (
            [dict(zone) for zone in zones]
            if zones is not None
            else self.list_zones(video_id=video_id, camera_id=camera_id, enabled=True)
        )
        return [_to_event_engine_zone(zone) for zone in source_zones]


def _zone_to_model_values(
    zone: Mapping[str, Any],
    *,
    include_id: bool = True,
) -> dict[str, Any]:
    values = {
        "name": zone["name"],
        "type": zone["zone_type"],
        "coordinates": {
            "polygon": zone["polygon"],
            "direction": zone.get("direction"),
            "counting_line": zone.get("counting_line"),
        },
        "status": "active" if zone.get("enabled", True) else "disabled",
        "metadata_json": {
            "video_id": zone.get("video_id"),
            "camera_id": zone.get("camera_id"),
            "version": int(zone.get("version") or 1),
        },
    }
    if include_id:
        values["id"] = zone["id"]
    return values


def _zone_from_model(row: Any) -> dict[str, Any]:
    coordinates = row.coordinates or {}
    metadata = row.metadata_json or {}
    return ZoneResponse(
        id=row.id,
        name=row.name,
        zone_type=row.type,
        polygon=coordinates.get("polygon") or [],
        direction=coordinates.get("direction"),
        counting_line=coordinates.get("counting_line"),
        enabled=row.status != "disabled",
        video_id=metadata.get("video_id"),
        camera_id=metadata.get("camera_id"),
        version=int(metadata.get("version") or 1),
    ).model_dump()
