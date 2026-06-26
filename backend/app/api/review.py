from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analysis.review_artifacts import (
    ReviewArtifactError,
    ReviewStateTransitionError,
)
from app.db.session import get_db
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
from app.services.event_lifecycle_service import EventLifecycleService
from app.services.review_service import ReviewService


router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/events", response_model=ReviewEventListResponse)
def list_review_events(
    run_id: str | None = Query(default=None),
    review_status: str | None = Query(default=None, alias="status"),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ReviewEventListResponse:
    if run_id is None or not run_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="run_id is required",
        )
    lifecycle = EventLifecycleService(db)
    if lifecycle.has_db_events(run_id=run_id):
        return ReviewEventListResponse(
            **lifecycle.list_review_events(
                run_id=run_id,
                status=review_status,
                event_type=event_type,
                limit=limit,
                offset=offset,
            )
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
    db: Session = Depends(get_db),
) -> ReviewEventDetailResponse:
    lifecycle = EventLifecycleService(db)
    if lifecycle.has_db_event(event_id, run_id=run_id):
        return ReviewEventDetailResponse(
            **lifecycle.get_review_event(run_id=run_id, event_id=event_id)
        )
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
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="confirm", db=db)


@router.post("/events/{event_id}/false-positive", response_model=ReviewActionResponse)
def mark_review_event_false_positive(
    event_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    return _apply_review_action(
        event_id,
        payload,
        action="mark_false_positive",
        db=db,
    )


@router.post("/events/{event_id}/ignore", response_model=ReviewActionResponse)
def ignore_review_event(
    event_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="ignore", db=db)


@router.post("/events/{event_id}/resolve", response_model=ReviewActionResponse)
def resolve_review_event(
    event_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    return _apply_review_action(event_id, payload, action="resolve", db=db)


@router.post("/comments", response_model=ReviewActionResponse)
def create_review_comment(
    payload: ReviewCommentCreate,
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    lifecycle = EventLifecycleService(db)
    if lifecycle.has_db_event(payload.event_id, run_id=payload.run_id):
        try:
            response = lifecycle.apply_review_action(
                run_id=payload.run_id,
                event_id=payload.event_id,
                action="comment",
                comment=payload.comment,
                reviewer=payload.reviewer,
                alert_id=payload.alert_id,
            )
            db.commit()
            return ReviewActionResponse(**response)
        except KeyError as exc:
            raise _not_found("event not found") from exc
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
    db: Session = Depends(get_db),
) -> ReviewCommentsResponse:
    lifecycle = EventLifecycleService(db)
    if lifecycle.has_db_events(run_id=run_id) or lifecycle.has_db_review_comments(
        run_id=run_id,
        event_id=event_id,
    ):
        return ReviewCommentsResponse(
            **lifecycle.query_review_comments(
                run_id=run_id,
                event_id=event_id,
                limit=limit,
                offset=offset,
            )
        )
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
    db: Session = Depends(get_db),
) -> FalseNegativeResponse:
    lifecycle = EventLifecycleService(db)
    if lifecycle.runs.get(payload.run_id) is not None:
        try:
            response = lifecycle.add_false_negative(
                run_id=payload.run_id,
                record=payload.model_dump(),
            )
            db.commit()
            return FalseNegativeResponse(**response)
        except KeyError as exc:
            raise _not_found("analysis run not found") from exc
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


@router.post("/events/false-negative")
def create_event_false_negative(
    payload: FalseNegativeCreate,
    db: Session = Depends(get_db),
) -> dict:
    try:
        response = EventLifecycleService(db).add_false_negative(
            run_id=payload.run_id,
            record=payload.model_dump(),
        )
        db.commit()
        return response
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc


@router.post("/events/{event_id}/rerun-rule")
def request_event_rule_rerun(
    event_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        response = EventLifecycleService(db).create_rule_rerun_request(
            run_id=payload.run_id,
            event_id=event_id,
            reviewer=payload.reviewer,
            comment=payload.comment,
        )
        db.commit()
        return response
    except KeyError as exc:
        raise _not_found("event not found") from exc


def _apply_review_action(
    event_id: str,
    payload: ReviewActionRequest,
    *,
    action: str,
    db: Session,
) -> ReviewActionResponse:
    lifecycle = EventLifecycleService(db)
    if lifecycle.has_db_event(event_id, run_id=payload.run_id):
        try:
            response = lifecycle.apply_review_action(
                run_id=payload.run_id,
                event_id=event_id,
                action=action,
                comment=payload.comment,
                reviewer=payload.reviewer,
                alert_id=payload.alert_id,
            )
            db.commit()
            return ReviewActionResponse(**response)
        except KeyError as exc:
            raise _not_found("event not found") from exc
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
