from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.cv.frame_reader import read_video_metadata
from app.schemas.processing import DetectionProcessRequest, DetectionProcessResponse
from app.services.detection_service import DetectionRunParams
from app.services.trajectory_service import TrajectoryRunParams
from app.services.tracking_service import TrackingRunParams
from app.schemas.video import VideoResponse, VideoStatusResponse
from app.services.processing_service import processing_service
from app.services.video_service import video_registry


router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse)
async def upload_video(file: UploadFile = File(...)) -> VideoResponse:
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
    target_path.write_bytes(content)

    metadata = read_video_metadata(target_path)
    record = video_registry.create_video(
        filename=file.filename,
        file_path=str(target_path),
        metadata=metadata,
    )
    return VideoResponse(**record)


@router.get("", response_model=list[VideoResponse])
def list_videos() -> list[VideoResponse]:
    return [VideoResponse(**record) for record in video_registry.list_videos()]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: str) -> VideoResponse:
    return VideoResponse(**_get_video_or_404(video_id))


@router.post("/{video_id}/process", response_model=DetectionProcessResponse)
def process_video(
    video_id: str,
    request: DetectionProcessRequest | None = None,
) -> DetectionProcessResponse:
    video = _get_video_or_404(video_id)
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
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DetectionProcessResponse(**task["result"])


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(video_id: str) -> VideoStatusResponse:
    video = _get_video_or_404(video_id)
    task = processing_service.get_latest_task(video_id)
    return VideoStatusResponse(
        video_id=video["id"],
        status=video["status"],
        latest_task=task,
    )


def _get_video_or_404(video_id: str) -> dict:
    try:
        return video_registry.get_video(video_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video not found",
        ) from exc
