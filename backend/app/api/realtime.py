from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.realtime_service import realtime_preview_service


router = APIRouter(prefix="/api/realtime", tags=["realtime"])


@router.post("/{camera_id}/start")
def start_realtime_preview(
    camera_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        response = realtime_preview_service.start(camera_id, db)
        db.commit()
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
) -> dict[str, Any]:
    try:
        response = realtime_preview_service.stop(camera_id, db)
        db.commit()
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
