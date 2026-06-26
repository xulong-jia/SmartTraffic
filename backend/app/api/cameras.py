from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import audit_log
from app.core.identity import Actor, get_actor, require_permission
from app.db.session import get_db
from app.schemas.camera import (
    CameraCreate,
    CameraDeleteResponse,
    CameraResponse,
    CameraSourceType,
    CameraUpdate,
)
from app.services.camera_service import CameraService


router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> CameraResponse:
    require_permission(actor, "manage_config")
    try:
        record = CameraService(db).create_camera(payload.model_dump())
        db.commit()
        audit_log(
            "camera.create",
            actor=actor,
            resource_type="camera",
            resource_id=record["id"],
        )
        return CameraResponse(**record)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[CameraResponse])
def list_cameras(
    source_type: CameraSourceType | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CameraResponse]:
    return [
        CameraResponse(**record)
        for record in CameraService(db).list_cameras(
            source_type=source_type,
            enabled=enabled,
        )
    ]


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)) -> CameraResponse:
    try:
        return CameraResponse(**CameraService(db).get_camera(camera_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.patch("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> CameraResponse:
    require_permission(actor, "manage_config")
    try:
        record = CameraService(db).update_camera(
            camera_id,
            payload.model_dump(exclude_unset=True),
        )
        db.commit()
        audit_log(
            "camera.update",
            actor=actor,
            resource_type="camera",
            resource_id=camera_id,
        )
        return CameraResponse(**record)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{camera_id}", response_model=CameraDeleteResponse)
def delete_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> CameraDeleteResponse:
    require_permission(actor, "manage_config")
    deleted = CameraService(db).delete_camera(camera_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        )
    db.commit()
    audit_log(
        "camera.delete",
        actor=actor,
        resource_type="camera",
        resource_id=camera_id,
    )
    return CameraDeleteResponse(deleted=True, camera_id=camera_id)


@router.post("/{camera_id}/enable", response_model=CameraResponse)
def enable_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> CameraResponse:
    require_permission(actor, "manage_config")
    try:
        record = CameraService(db).enable_camera(camera_id)
        db.commit()
        audit_log(
            "camera.enable",
            actor=actor,
            resource_type="camera",
            resource_id=camera_id,
        )
        return CameraResponse(**record)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.post("/{camera_id}/disable", response_model=CameraResponse)
def disable_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> CameraResponse:
    require_permission(actor, "manage_config")
    try:
        record = CameraService(db).disable_camera(camera_id)
        db.commit()
        audit_log(
            "camera.disable",
            actor=actor,
            resource_type="camera",
            resource_id=camera_id,
        )
        return CameraResponse(**record)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc
