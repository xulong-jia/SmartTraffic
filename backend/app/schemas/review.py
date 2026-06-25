from typing import Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal[
    "pending",
    "confirmed",
    "false_positive",
    "false_negative",
    "ignored",
    "resolved",
]
ReviewAction = Literal[
    "confirm",
    "mark_false_positive",
    "add_false_negative",
    "ignore",
    "resolve",
    "comment",
]

REVIEW_STATUSES = {
    "pending",
    "confirmed",
    "false_positive",
    "false_negative",
    "ignored",
    "resolved",
}
REVIEW_ACTIONS = {
    "confirm",
    "mark_false_positive",
    "add_false_negative",
    "ignore",
    "resolve",
    "comment",
}


class ReviewCommentRecord(BaseModel):
    review_id: str
    run_id: str
    event_id: str | None = None
    alert_id: str | None = None
    action: ReviewAction
    before_status: ReviewStatus | None = None
    after_status: ReviewStatus
    comment: str = ""
    reviewer: str = "local_reviewer"
    created_at: str
    source: str = "review_center"


class EventReviewStateItem(BaseModel):
    event_id: str
    status: ReviewStatus
    last_action: ReviewAction
    last_review_id: str
    reviewer: str = "local_reviewer"
    updated_at: str
    comment_count: int = 0


class EventReviewState(BaseModel):
    schema_version: str = "stage7b.v1"
    run_id: str
    updated_at: str | None = None
    events: dict[str, EventReviewStateItem] = Field(default_factory=dict)


class FalseNegativeEventRecord(BaseModel):
    false_negative_id: str
    run_id: str
    expected_event_type: str
    zone_id: str | None = None
    track_id: int | None = None
    start_frame: int | None = None
    end_frame: int | None = None
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    description: str = ""
    reviewer: str = "local_reviewer"
    created_at: str
    status: Literal["false_negative"] = "false_negative"
    source: str = "review_center"
