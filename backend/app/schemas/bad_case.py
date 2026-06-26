from typing import Literal

from pydantic import BaseModel, Field, field_validator


BadCaseType = Literal[
    "false_positive",
    "false_negative",
    "detection_miss",
    "detection_false_positive",
    "tracking_fragmentation",
    "id_switch",
    "track_lost",
    "trajectory_error",
    "event_rule_error",
    "rule_error",
    "zone_config_error",
    "annotation_error",
    "other",
]
BadCaseModule = Literal[
    "detector",
    "tracker",
    "trajectory",
    "event_engine",
    "zone_config",
    "review",
    "evaluation",
    "review_center",
    "evaluation_center",
    "visualization",
    "other",
]
BadCaseStatus = Literal["open", "triaged", "fixed", "verified", "ignored", "wont_fix"]
BadCaseSource = Literal["manual", "review_center", "evaluation", "evaluation_center", "import"]

BAD_CASE_TYPES = {
    "false_positive",
    "false_negative",
    "detection_miss",
    "detection_false_positive",
    "tracking_fragmentation",
    "id_switch",
    "track_lost",
    "trajectory_error",
    "event_rule_error",
    "rule_error",
    "zone_config_error",
    "annotation_error",
    "other",
}
BAD_CASE_MODULES = {
    "detector",
    "tracker",
    "trajectory",
    "event_engine",
    "zone_config",
    "review",
    "evaluation",
    "review_center",
    "evaluation_center",
    "visualization",
    "other",
}
BAD_CASE_STATUSES = {"open", "triaged", "fixed", "verified", "ignored", "wont_fix"}
BAD_CASE_SOURCES = {"manual", "review_center", "evaluation", "evaluation_center", "import"}


class BadCaseRecord(BaseModel):
    case_id: str
    run_id: str
    video_id: str | None = None
    event_id: str | None = None
    track_id: int | None = None
    frame_index: int | None = None
    case_type: BadCaseType
    module: BadCaseModule
    description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    root_cause: str = ""
    snapshot_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: BadCaseStatus = "open"
    source: BadCaseSource = "manual"
    linked_review_id: str | None = None
    linked_failed_case_id: str | None = None
    created_at: str
    updated_at: str

    @field_validator("snapshot_path")
    @classmethod
    def snapshot_path_must_be_relative(cls, value: str | None) -> str | None:
        return _validate_snapshot_path(value)


class BadCaseCreateRequest(BaseModel):
    video_id: str | None = None
    event_id: str | None = None
    track_id: int | None = None
    frame_index: int | None = None
    case_type: BadCaseType
    module: BadCaseModule
    description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    root_cause: str = ""
    snapshot_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: BadCaseStatus = "open"
    source: BadCaseSource = "manual"
    linked_review_id: str | None = None
    linked_failed_case_id: str | None = None

    @field_validator("snapshot_path")
    @classmethod
    def snapshot_path_must_be_relative(cls, value: str | None) -> str | None:
        return _validate_snapshot_path(value)


class BadCaseCreateApiRequest(BadCaseCreateRequest):
    run_id: str


class BadCaseUpdateRequest(BaseModel):
    status: BadCaseStatus | None = None
    root_cause: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    snapshot_path: str | None = None
    linked_failed_case_id: str | None = None

    @field_validator("snapshot_path")
    @classmethod
    def snapshot_path_must_be_relative(cls, value: str | None) -> str | None:
        return _validate_snapshot_path(value)


class BadCaseUpdateApiRequest(BadCaseUpdateRequest):
    run_id: str | None = None


class BadCaseFromReviewRequest(BaseModel):
    run_id: str
    event_id: str | None = None
    review_id: str | None = None
    case_type: BadCaseType | None = None
    module: BadCaseModule = "review_center"
    description: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    root_cause: str | None = None
    tags: list[str] | None = None


class BadCaseFromFailedCaseRequest(BaseModel):
    run_id: str
    failed_case_id: str
    case_type: BadCaseType | None = None
    module: BadCaseModule | None = None
    description: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    root_cause: str | None = None
    tags: list[str] | None = None


class BadCaseUpdateAuditRecord(BaseModel):
    run_id: str
    case_id: str
    updated_fields: list[str]
    updated_at: str
    source: str = "bad_case_service"


class BadCaseSummary(BaseModel):
    total: int
    by_type: dict[str, int] = Field(default_factory=dict)
    by_module: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    by_tag: dict[str, int] = Field(default_factory=dict)
    top_tags: dict[str, int] = Field(default_factory=dict)


class BadCaseListResponse(BaseModel):
    items: list[BadCaseRecord]
    total: int
    limit: int
    offset: int
    summary: BadCaseSummary


class BadCaseDetailResponse(BadCaseRecord):
    pass


def _validate_snapshot_path(value: str | None) -> str | None:
    if value is None:
        return value
    parts = value.replace("\\", "/").split("/")
    if value.startswith("/") or ".." in parts:
        raise ValueError("snapshot_path must be a relative path inside the run directory")
    return value
