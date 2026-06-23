from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertListResponse,
    AlertResponse,
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    run_id: str | None = Query(default=None),
    alert_status: str | None = Query(default=None, alias="status"),
    level: str | None = Query(default=None),
) -> AlertListResponse:
    alerts = AlertService().list_alerts(
        run_id=run_id,
        status=alert_status,
        level=level,
    )
    return AlertListResponse(
        alerts=[AlertResponse(**alert) for alert in alerts],
        total=len(alerts),
        run_id=run_id,
        status=alert_status,
        level=level,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str) -> AlertResponse:
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
) -> AlertResponse:
    try:
        return AlertResponse(
            **AlertService().acknowledge_alert(
                alert_id,
                acknowledged_by=payload.acknowledged_by if payload else None,
            )
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: str) -> AlertResponse:
    try:
        return AlertResponse(**AlertService().resolve_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc


@router.patch("/{alert_id}/ignore", response_model=AlertResponse)
def ignore_alert(alert_id: str) -> AlertResponse:
    try:
        return AlertResponse(**AlertService().ignore_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert not found",
        ) from exc
