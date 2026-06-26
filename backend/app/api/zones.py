from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate
from app.services.zone_service import ZoneDbService


router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_db),
) -> ZoneResponse:
    try:
        zone = ZoneDbService(db).create_zone(payload)
        db.commit()
        return ZoneResponse(**zone)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ZoneResponse])
def list_zones(
    video_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ZoneResponse]:
    return [
        ZoneResponse(**zone)
        for zone in ZoneDbService(db).list_zones(video_id=video_id, enabled=enabled)
    ]


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(
    zone_id: str,
    db: Session = Depends(get_db),
) -> ZoneResponse:
    try:
        return ZoneResponse(**ZoneDbService(db).get_zone(zone_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone not found",
        ) from exc


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: str,
    payload: ZoneUpdate,
    db: Session = Depends(get_db),
) -> ZoneResponse:
    try:
        zone = ZoneDbService(db).update_zone(zone_id, payload)
        db.commit()
        return ZoneResponse(**zone)
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
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    try:
        ZoneDbService(db).delete_zone(zone_id)
        db.commit()
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone not found",
        ) from exc
    return {"id": zone_id, "deleted": True}
