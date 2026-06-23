from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.event_rule import EventRuleCreate, EventRuleResponse, EventRuleUpdate
from app.services.event_rule_service import event_rule_service


router = APIRouter(prefix="/api/event-rules", tags=["event-rules"])


@router.post("", response_model=EventRuleResponse, status_code=status.HTTP_201_CREATED)
def create_event_rule(payload: EventRuleCreate) -> EventRuleResponse:
    try:
        return EventRuleResponse(**event_rule_service.create_rule(payload))
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
) -> list[EventRuleResponse]:
    return [
        EventRuleResponse(**rule)
        for rule in event_rule_service.list_rules(
            event_type=event_type,
            enabled=enabled,
            zone_id=zone_id,
        )
    ]


@router.get("/{rule_id}", response_model=EventRuleResponse)
def get_event_rule(rule_id: str) -> EventRuleResponse:
    try:
        return EventRuleResponse(**event_rule_service.get_rule(rule_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event rule not found",
        ) from exc


@router.patch("/{rule_id}", response_model=EventRuleResponse)
def update_event_rule(
    rule_id: str,
    payload: EventRuleUpdate,
) -> EventRuleResponse:
    try:
        return EventRuleResponse(**event_rule_service.update_rule(rule_id, payload))
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
def delete_event_rule(rule_id: str) -> dict[str, str | bool]:
    try:
        event_rule_service.delete_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event rule not found",
        ) from exc
    return {"id": rule_id, "deleted": True}
