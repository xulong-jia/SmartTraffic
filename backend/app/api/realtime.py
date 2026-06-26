from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.audit import audit_log
from app.core.identity import Actor, get_actor, require_permission
from app.services.realtime_service import realtime_preview_service


router = APIRouter(prefix="/api/realtime", tags=["realtime"])


@router.post("/{camera_id}/start")
def start_realtime_preview(
    camera_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> dict[str, Any]:
    require_permission(actor, "operate")
    try:
        response = realtime_preview_service.start(camera_id, db, actor=actor)
        db.commit()
        audit_log(
            "realtime.start",
            actor=actor,
            resource_type="camera",
            resource_id=camera_id,
        )
        return response
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


@router.post("/{camera_id}/stop")
def stop_realtime_preview(
    camera_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> dict[str, Any]:
    require_permission(actor, "operate")
    try:
        response = realtime_preview_service.stop(camera_id, db, actor=actor)
        db.commit()
        audit_log(
            "realtime.stop",
            actor=actor,
            resource_type="camera",
            resource_id=camera_id,
        )
        return response
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.get("/{camera_id}/status")
def get_realtime_status(
    camera_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return realtime_preview_service.status(camera_id, db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.get("/{camera_id}/recent-frames")
def get_recent_frames(
    camera_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return realtime_preview_service.recent_frames(camera_id, db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.get("/{camera_id}/recent-events")
def get_recent_events(
    camera_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return realtime_preview_service.recent_events(camera_id, db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc


@router.get("/{camera_id}/recent-alerts")
def get_recent_alerts(
    camera_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return realtime_preview_service.recent_alerts(camera_id, db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camera not found",
        ) from exc
