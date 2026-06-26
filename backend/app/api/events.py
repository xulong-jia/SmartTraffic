from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.event_api_service import EventApiService


router = APIRouter(prefix="/api/events", tags=["events"])


class EventStatusUpdate(BaseModel):
    status: str


class EventBadCaseCreate(BaseModel):
    case_type: str = "other"
    module: str = "event_engine"
    description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    tags: list[str] = Field(default_factory=list)


@router.get("")
def list_events(
    run_id: str | None = Query(default=None),
    video_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    track_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return EventApiService(db).list_events(
        run_id=run_id,
        video_id=video_id,
        event_type=event_type,
        status=status_filter,
        severity=severity,
        track_id=track_id,
    )


@router.get("/{event_id}")
def get_event(
    event_id: str,
    run_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return EventApiService(db).get_event(event_id, run_id=run_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        ) from exc


@router.patch("/{event_id}/status")
def update_event_status(
    event_id: str,
    payload: EventStatusUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        event = EventApiService(db).update_status(event_id, payload.status)
        db.commit()
        return event
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{event_id}/bad-case", status_code=status.HTTP_201_CREATED)
def create_event_bad_case(
    event_id: str,
    payload: EventBadCaseCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        bad_case = EventApiService(db).create_bad_case(
            event_id,
            payload.model_dump(exclude_none=True),
        )
        db.commit()
        return bad_case
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event not found",
        ) from exc
