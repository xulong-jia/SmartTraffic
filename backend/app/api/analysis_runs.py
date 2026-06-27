from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.alert_service import AlertService
from app.services.traffic_analysis_service import traffic_analysis_service


router = APIRouter(prefix="/api/analysis-runs", tags=["analysis-runs"])


@router.get("")
def list_analysis_runs(
    run_status: str | None = Query(default=None, alias="status"),
    video_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return traffic_analysis_service.list_runs(
        status=run_status,
        video_id=video_id,
        limit=limit,
        offset=offset,
        db=db,
    )


@router.get("/{run_id}")
def get_analysis_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.get_run(run_id, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/manifest")
def get_analysis_run_manifest(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_manifest(run_id, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/flow-counts")
def get_analysis_run_flow_counts(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_flow_counts(run_id, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="flow counts artifact not found",
        ) from exc


@router.get("/{run_id}/zone-statistics")
def get_analysis_run_zone_statistics(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_zone_statistics(run_id, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="zone statistics artifact not found",
        ) from exc


@router.get("/{run_id}/detections")
def get_analysis_run_detections(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_detections(
            run_id,
            limit=limit,
            db=db,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/tracks")
def get_analysis_run_tracks(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_tracks(run_id, limit=limit, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/trajectory-points")
def get_analysis_run_trajectory_points(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
    track_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_trajectory_points(
            run_id,
            limit=limit,
            track_id=track_id,
            db=db,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="trajectory artifacts not found",
        ) from exc


@router.get("/{run_id}/events")
def get_analysis_run_events(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
    event_type: str | None = Query(default=None),
    rule_id: str | None = Query(default=None),
    track_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_events(
            run_id,
            limit=limit,
            event_type=event_type,
            rule_id=rule_id,
            track_id=track_id,
            db=db,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event artifacts not found",
        ) from exc


@router.post("/{run_id}/alerts/generate")
def generate_analysis_run_alerts(run_id: str) -> dict:
    try:
        return AlertService().generate_alerts(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="event artifacts not found",
        ) from exc


@router.get("/{run_id}/alerts")
def get_analysis_run_alerts(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
    alert_status: str | None = Query(default=None, alias="status"),
    level: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return traffic_analysis_service.read_run_alerts(
            run_id,
            limit=limit,
            status=alert_status,
            level=level,
            event_type=event_type,
            db=db,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="alert artifacts not found",
        ) from exc
