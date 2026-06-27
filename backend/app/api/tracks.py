from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import TrackRepository, TrafficAnalysisRunRepository
from app.services.traffic_analysis_service import traffic_analysis_service

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("")
def list_tracks(
    run_id: str | None = Query(default=None),
    video_id: str | None = Query(default=None),
    track_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=0, le=1000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = TrackRepository(db).list(run_id=run_id, video_id=video_id)
    if track_id is not None:
        rows = [row for row in rows if str(row.track_id) == str(track_id)]
    if rows or run_id is None or TrafficAnalysisRunRepository(db).get(run_id) is not None:
        limited = rows[:limit] if limit > 0 else []
        return {
            "run_id": run_id,
            "video_id": _first_video_id(limited, video_id),
            "summary": {"total_tracks": len(rows)},
            "frames": _group_by_frame(limited),
            "rows": [_track_payload(row) for row in limited],
            "limit": limit,
            "track_id": track_id,
            "source": "db",
        }
    try:
        return traffic_analysis_service.read_run_tracks(run_id, limit=limit, db=db)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tracks not found",
        ) from exc


def _track_payload(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "video_id": row.video_id,
        "track_id": row.track_id,
        "class_name": row.class_name,
        "start_frame": row.start_frame,
        "end_frame": row.end_frame,
        "confidence": row.confidence,
        "metadata": row.metadata_json or {},
    }


def _group_by_frame(rows: list[Any]) -> list[dict[str, Any]]:
    frames: dict[int, dict[str, Any]] = {}
    for row in rows:
        frame_index = int(row.start_frame or 0)
        frame = frames.setdefault(frame_index, {"frame_index": frame_index, "tracks": []})
        frame["tracks"].append(_track_payload(row))
    return [frames[index] for index in sorted(frames)]


def _first_video_id(rows: list[Any], fallback: str | None) -> str:
    for row in rows:
        if row.video_id:
            return str(row.video_id)
    return fallback or ""
