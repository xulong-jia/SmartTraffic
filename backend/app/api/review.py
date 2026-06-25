from fastapi import APIRouter, HTTPException, Query, status

from app.analysis.review_artifacts import (
    ReviewArtifactError,
    ReviewStateTransitionError,
)
from app.schemas.review import (
    FalseNegativeCreate,
    FalseNegativeResponse,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewCommentCreate,
    ReviewCommentsResponse,
    ReviewEventDetailResponse,
    ReviewEventListResponse,
)
from app.services.review_service import ReviewService


router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/events", response_model=ReviewEventListResponse)
def list_review_events(
    run_id: str | None = Query(default=None),
    review_status: str | None = Query(default=None, alias="status"),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ReviewEventListResponse:
    if run_id is None or not run_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="run_id is required",
        )
    try:
        return ReviewEventListResponse(
            **ReviewService().list_review_events(
                run_id=run_id,
                status=review_status,
                event_type=event_type,
                limit=limit,
                offset=offset,
            )
        )
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


@router.get("/events/{event_id}", response_model=ReviewEventDetailResponse)
def get_review_event(
    event_id: str,
    run_id: str = Query(...),
) -> ReviewEventDetailResponse:
    try:
        return ReviewEventDetailResponse(
            **ReviewService().get_review_event(run_id=run_id, event_id=event_id)
        )
    except KeyError as exc:
        raise _not_found("event not found") from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


@router.post("/events/{event_id}/confirm", response_model=ReviewActionResponse)
def confirm_review_event(
    event_id: str,
    payload: ReviewActionRequest,
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="confirm")


@router.post("/events/{event_id}/false-positive", response_model=ReviewActionResponse)
def mark_review_event_false_positive(
    event_id: str,
    payload: ReviewActionRequest,
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="mark_false_positive")


@router.post("/events/{event_id}/ignore", response_model=ReviewActionResponse)
def ignore_review_event(
    event_id: str,
    payload: ReviewActionRequest,
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="ignore")


@router.post("/events/{event_id}/resolve", response_model=ReviewActionResponse)
def resolve_review_event(
    event_id: str,
    payload: ReviewActionRequest,
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="resolve")


@router.post("/comments", response_model=ReviewActionResponse)
def create_review_comment(payload: ReviewCommentCreate) -> ReviewActionResponse:
    try:
        return ReviewActionResponse(
            **ReviewService().apply_action(
                run_id=payload.run_id,
                event_id=payload.event_id,
                action="comment",
                comment=payload.comment,
                reviewer=payload.reviewer,
                alert_id=payload.alert_id,
            )
        )
    except KeyError as exc:
        raise _not_found("event not found") from exc
    except ReviewStateTransitionError as exc:
        raise _bad_request(str(exc)) from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


@router.get("/comments", response_model=ReviewCommentsResponse)
def list_review_comments(
    run_id: str = Query(...),
    event_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ReviewCommentsResponse:
    try:
        return ReviewCommentsResponse(
            **ReviewService().query_review_comments(
                run_id=run_id,
                event_id=event_id,
                limit=limit,
                offset=offset,
            )
        )
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


@router.post("/false-negatives", response_model=FalseNegativeResponse)
def create_false_negative(
    payload: FalseNegativeCreate,
) -> FalseNegativeResponse:
    try:
        return FalseNegativeResponse(
            **ReviewService().add_false_negative(
                run_id=payload.run_id,
                record=payload.model_dump(),
            )
        )
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


def _apply_review_action(
    event_id: str,
    payload: ReviewActionRequest,
    *,
    action: str,
) -> ReviewActionResponse:
    try:
        return ReviewActionResponse(
            **ReviewService().apply_action(
                run_id=payload.run_id,
                event_id=event_id,
                action=action,
                comment=payload.comment,
                reviewer=payload.reviewer,
                alert_id=payload.alert_id,
            )
        )
    except KeyError as exc:
        raise _not_found("event not found") from exc
    except ReviewStateTransitionError as exc:
        raise _bad_request(str(exc)) from exc
    except ReviewArtifactError as exc:
        raise _bad_request("invalid review artifact") from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
