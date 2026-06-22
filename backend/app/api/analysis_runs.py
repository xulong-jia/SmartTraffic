from fastapi import APIRouter, HTTPException, Query, status

from app.services.traffic_analysis_service import traffic_analysis_service


router = APIRouter(prefix="/api/analysis-runs", tags=["analysis-runs"])


@router.get("")
def list_analysis_runs() -> list[dict]:
    return traffic_analysis_service.list_runs()


@router.get("/{run_id}")
def get_analysis_run(run_id: str) -> dict:
    try:
        return traffic_analysis_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/detections")
def get_analysis_run_detections(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
) -> dict:
    try:
        return traffic_analysis_service.read_run_detections(run_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc


@router.get("/{run_id}/tracks")
def get_analysis_run_tracks(
    run_id: str,
    limit: int = Query(default=100, ge=0, le=1000),
) -> dict:
    try:
        return traffic_analysis_service.read_run_tracks(run_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis run not found",
        ) from exc
