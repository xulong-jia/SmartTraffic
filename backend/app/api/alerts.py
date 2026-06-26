from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import audit_log
from app.core.identity import Actor, get_actor, require_permission
from app.db.session import get_db
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertListResponse,
    AlertResponse,
)
from app.services.alert_service import AlertService
from app.services.event_lifecycle_service import EventLifecycleService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    run_id: str | None = Query(default=None),
    alert_status: str | None = Query(default=None, alias="status"),
    level: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    lifecycle = EventLifecycleService(db)
    db_alerts = lifecycle.list_alerts(
        run_id=run_id,
        status=alert_status,
        level=level,
    )
    has_db_alerts = run_id is not None and bool(lifecycle.list_alerts(run_id=run_id))
    alerts = (
        db_alerts
        if db_alerts or has_db_alerts
        else AlertService().list_alerts(
            run_id=run_id,
            status=alert_status,
            level=level,
        )
    )
    return AlertListResponse(
        alerts=[AlertResponse(**alert) for alert in alerts],
        total=len(alerts),
        run_id=run_id,
        status=alert_status,
        level=level,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)) -> AlertResponse:
    try:
        return AlertResponse(**EventLifecycleService(db).get_alert(alert_id))
    except KeyError:
        pass
    try:
        return AlertResponse(**AlertService().get_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledgeRequest | None = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> AlertResponse:
    require_permission(actor, "ack_alert")
    acknowledged_by = payload.acknowledged_by if payload and payload.acknowledged_by else actor.name
    try:
        response = AlertResponse(
            **EventLifecycleService(db).acknowledge_alert(
                alert_id,
                acknowledged_by=acknowledged_by,
            )
        )
        db.commit()
        audit_log(
            "alert.acknowledge",
            actor=actor,
            resource_type="alert",
            resource_id=alert_id,
        )
        return response
    except KeyError:
        pass
    try:
        return AlertResponse(
            **AlertService().acknowledge_alert(
                alert_id,
                acknowledged_by=acknowledged_by,
            )
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> AlertResponse:
    require_permission(actor, "ack_alert")
    try:
        response = AlertResponse(**EventLifecycleService(db).resolve_alert(alert_id))
        db.commit()
        audit_log(
            "alert.resolve",
            actor=actor,
            resource_type="alert",
            resource_id=alert_id,
        )
        return response
    except KeyError:
        pass
    try:
        return AlertResponse(**AlertService().resolve_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc


@router.patch("/{alert_id}/ignore", response_model=AlertResponse)
def ignore_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> AlertResponse:
    require_permission(actor, "ack_alert")
    try:
        response = AlertResponse(**EventLifecycleService(db).ignore_alert(alert_id))
        db.commit()
        audit_log(
            "alert.ignore",
            actor=actor,
            resource_type="alert",
            resource_id=alert_id,
        )
        return response
    except KeyError:
        pass
    try:
        return AlertResponse(**AlertService().ignore_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc
