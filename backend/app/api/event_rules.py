from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.event_rule import EventRuleCreate, EventRuleResponse, EventRuleUpdate
from app.services.event_rule_service import EventRuleDbService


router = APIRouter(prefix="/api/event-rules", tags=["event-rules"])


@router.post("", response_model=EventRuleResponse, status_code=status.HTTP_201_CREATED)
def create_event_rule(
    payload: EventRuleCreate,
    db: Session = Depends(get_db),
) -> EventRuleResponse:
    try:
        rule = EventRuleDbService(db).create_rule(payload)
        db.commit()
        return EventRuleResponse(**rule)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[EventRuleResponse])
def list_event_rules(
    event_type: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[EventRuleResponse]:
    return [
        EventRuleResponse(**rule)
        for rule in EventRuleDbService(db).list_rules(
            event_type=event_type,
            enabled=enabled,
            zone_id=zone_id,
        )
    ]


@router.get("/{rule_id}", response_model=EventRuleResponse)
def get_event_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> EventRuleResponse:
    try:
        return EventRuleResponse(**EventRuleDbService(db).get_rule(rule_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event rule not found",
        ) from exc


@router.patch("/{rule_id}", response_model=EventRuleResponse)
def update_event_rule(
    rule_id: str,
    payload: EventRuleUpdate,
    db: Session = Depends(get_db),
) -> EventRuleResponse:
    try:
        rule = EventRuleDbService(db).update_rule(rule_id, payload)
        db.commit()
        return EventRuleResponse(**rule)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event rule not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{rule_id}")
def delete_event_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    try:
        EventRuleDbService(db).delete_rule(rule_id)
        db.commit()
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event rule not found",
        ) from exc
    return {"id": rule_id, "deleted": True}
