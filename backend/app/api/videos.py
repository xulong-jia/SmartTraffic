from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.cv.frame_reader import read_video_metadata
from app.db.session import get_db
from app.schemas.processing import DetectionProcessRequest, DetectionProcessResponse
from app.services.detection_service import DetectionRunParams
from app.services.trajectory_service import TrajectoryRunParams
from app.services.tracking_service import TrackingRunParams
from app.schemas.video import FrameResponse, VideoResponse, VideoStatusResponse
from app.services.processing_service import EventAlertProcessParams, processing_service
from app.services.video_service import VideoDbService


router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> VideoResponse:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filename is required",
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported video type: {suffix}",
        )

    settings.local_videos_dir.mkdir(parents=True, exist_ok=True)
    target_path = settings.local_videos_dir / Path(file.filename).name
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="uploaded video is empty",
        )
    max_upload_bytes = settings.max_upload_mb * 1024 * 1024
    if max_upload_bytes > 0 and len(content) > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"uploaded video exceeds {settings.max_upload_mb} MB limit",
        )
    target_path.write_bytes(content)

    try:
        metadata = read_video_metadata(target_path)
        _validate_uploaded_video_metadata(metadata, settings)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except (RuntimeError, ValueError, OSError) as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unable to read video metadata: {exc.__class__.__name__}",
        ) from exc
    record = VideoDbService(db).create_video(
        filename=file.filename,
        file_path=str(target_path),
        metadata=metadata,
    )
    db.commit()
    return VideoResponse(**record)


@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)) -> list[VideoResponse]:
    return [VideoResponse(**record) for record in VideoDbService(db).list_videos()]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
) -> VideoResponse:
    return VideoResponse(**_get_video_or_404(video_id, db))


@router.get("/{video_id}/frames", response_model=list[FrameResponse])
def list_video_frames(
    video_id: str,
    db: Session = Depends(get_db),
) -> list[FrameResponse]:
    try:
        return [
            FrameResponse(**record)
            for record in VideoDbService(db).list_frames(video_id)
        ]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video not found",
        ) from exc


@router.post("/{video_id}/process", response_model=DetectionProcessResponse)
def process_video(
    video_id: str,
    request: DetectionProcessRequest | None = None,
    db: Session = Depends(get_db),
) -> DetectionProcessResponse:
    video = _get_video_or_404(video_id, db)
    payload = request or DetectionProcessRequest()
    detector_dry_run = (
        payload.detector_dry_run
        if payload.detector_dry_run is not None
        else payload.dry_run
    )
    try:
        if payload.mode == "detection_only":
            params = DetectionRunParams(
                model_path=payload.model_path,
                conf_threshold=payload.conf_threshold,
                iou_threshold=payload.iou_threshold,
                image_size=payload.image_size,
                device=payload.device,
                dry_run=detector_dry_run,
                frame_stride=payload.frame_stride,
                max_frames=payload.max_frames,
                write_preview=bool(payload.write_preview),
            )
        elif payload.mode == "detection_tracking_trajectory":
            params = TrajectoryRunParams(
                model_path=payload.model_path,
                conf_threshold=payload.conf_threshold,
                iou_threshold=payload.iou_threshold,
                image_size=payload.image_size,
                device=payload.device,
                detector_dry_run=detector_dry_run,
                tracker_dry_run=payload.tracker_dry_run,
                frame_stride=payload.frame_stride,
                max_frames=payload.max_frames,
                write_preview=payload.write_preview,
                deepsort_max_age=payload.deepsort_max_age,
                deepsort_n_init=payload.deepsort_n_init,
                deepsort_max_iou_distance=payload.deepsort_max_iou_distance,
                deepsort_max_cosine_distance=payload.deepsort_max_cosine_distance,
                tracking_min_confidence=payload.tracking_min_confidence,
                tracking_target_classes=payload.tracking_target_classes,
                direction_window=(
                    payload.direction_window
                    if payload.direction_window is not None
                    else 2
                ),
                dwell_speed_threshold=(
                    payload.dwell_speed_threshold
                    if payload.dwell_speed_threshold is not None
                    else 1.0
                ),
                max_history_points=payload.max_history_points,
            )
        else:
            params = TrackingRunParams(
                model_path=payload.model_path,
                conf_threshold=payload.conf_threshold,
                iou_threshold=payload.iou_threshold,
                image_size=payload.image_size,
                device=payload.device,
                detector_dry_run=detector_dry_run,
                tracker_dry_run=payload.tracker_dry_run,
                frame_stride=payload.frame_stride,
                max_frames=payload.max_frames,
                write_preview=payload.write_preview,
                deepsort_max_age=payload.deepsort_max_age,
                deepsort_n_init=payload.deepsort_n_init,
                deepsort_max_iou_distance=payload.deepsort_max_iou_distance,
                deepsort_max_cosine_distance=payload.deepsort_max_cosine_distance,
                tracking_min_confidence=payload.tracking_min_confidence,
                tracking_target_classes=payload.tracking_target_classes,
            )
        task = processing_service.create_processing_task(
            video,
            params=params,
            mode=payload.mode,
            event_alert_params=EventAlertProcessParams(
                event_rules=payload.event_rules,
                zones=payload.zones,
                run_events=payload.run_events,
                generate_alerts=payload.generate_alerts,
                record_not_matched=payload.record_not_matched,
            ),
            db=db,
        )
        db.commit()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DetectionProcessResponse(**task["result"])


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(
    video_id: str,
    db: Session = Depends(get_db),
) -> VideoStatusResponse:
    video = _get_video_or_404(video_id, db)
    task = processing_service.get_latest_db_task(video_id, db)
    return VideoStatusResponse(
        video_id=video["id"],
        status=video["status"],
        latest_task=task,
    )


def _get_video_or_404(video_id: str, db: Session) -> dict:
    try:
        return VideoDbService(db).get_video(video_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video not found",
        ) from exc


def _validate_uploaded_video_metadata(metadata: dict, settings) -> None:
    duration = float(metadata.get("duration_seconds") or 0.0)
    max_duration = float(settings.max_video_duration_seconds or 0.0)
    if max_duration > 0 and duration > max_duration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "uploaded video duration exceeds "
                f"{settings.max_video_duration_seconds:g} seconds limit"
            ),
        )

    allowed_codecs = {
        _normalize_upload_codec(codec)
        for codec in settings.allowed_video_codecs
    }
    raw_codec = str(metadata.get("codec") or "").strip().lower()
    codec = _normalize_upload_codec(raw_codec)
    if allowed_codecs:
        if not codec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unable to determine video codec",
            )
        if codec not in allowed_codecs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unsupported video codec: {raw_codec}",
            )


def _normalize_upload_codec(codec: str) -> str:
    aliases = {
        # OpenCV/FFmpeg often reads videos written as mp4v back as fmp4.
        "fmp4": "mp4v",
    }
    normalized = codec.strip().lower()
    return aliases.get(normalized, normalized)
