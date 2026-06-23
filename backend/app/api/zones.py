from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate
from app.services.zone_service import zone_service


router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate) -> ZoneResponse:
    try:
        return ZoneResponse(**zone_service.create_zone(payload))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ZoneResponse])
def list_zones(
    video_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
) -> list[ZoneResponse]:
    return [
        ZoneResponse(**zone)
        for zone in zone_service.list_zones(video_id=video_id, enabled=enabled)
    ]


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: str) -> ZoneResponse:
    try:
        return ZoneResponse(**zone_service.get_zone(zone_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone not found",
        ) from exc


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(zone_id: str, payload: ZoneUpdate) -> ZoneResponse:
    try:
        return ZoneResponse(**zone_service.update_zone(zone_id, payload))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{zone_id}")
def delete_zone(zone_id: str) -> dict[str, str | bool]:
    try:
        zone_service.delete_zone(zone_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone not found",
        ) from exc
    return {"id": zone_id, "deleted": True}
