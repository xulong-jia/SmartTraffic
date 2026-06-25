from typing import Any, Literal

from pydantic import BaseModel, Field


EvaluationType = Literal[
    "event",
    "flow_counting",
    "trajectory",
    "detection",
    "tracking",
    "regression",
]
EvaluationRunStatus = Literal["completed", "failed"]


class EvaluationDatasetRecord(BaseModel):
    dataset_id: str
    name: str
    dataset_type: EvaluationType | str
    source: str = "custom_annotation"
    annotation_path: str | None = None
    expected_events_path: str | None = None
    expected_counts_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class EvaluationDatasetCreate(BaseModel):
    dataset_id: str
    name: str
    dataset_type: EvaluationType | str
    source: str = "custom_annotation"
    annotation_path: str | None = None
    expected_events_path: str | None = None
    expected_counts_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationDatasetRegistry(BaseModel):
    schema_version: str
    datasets: list[EvaluationDatasetRecord] = Field(default_factory=list)


class EvaluationRunRecord(BaseModel):
    evaluation_run_id: str
    dataset_id: str | None = None
    run_id: str
    evaluation_type: EvaluationType | str
    status: EvaluationRunStatus | str
    started_at: str
    finished_at: str
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluationResultRecord(BaseModel):
    evaluation_result_id: str
    evaluation_run_id: str
    run_id: str
    dataset_id: str | None = None
    evaluation_type: EvaluationType | str
    metric_name: str
    metric_value: float | int | str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class FailedCaseRecord(BaseModel):
    failed_case_id: str
    evaluation_run_id: str
    run_id: str
    dataset_id: str | None = None
    failure_type: str
    module: str
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    frame_range: dict[str, int | None] = Field(default_factory=dict)
    suggested_bad_case_type: str | None = None
    created_at: str


class EvaluationSummaryArtifact(BaseModel):
    schema_version: str
    run_id: str
    generated_at: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    failed_cases: list[FailedCaseRecord] = Field(default_factory=list)


class EvaluationDatasetListResponse(BaseModel):
    schema_version: str
    datasets: list[EvaluationDatasetRecord] = Field(default_factory=list)


class EvaluationRunRequest(BaseModel):
    run_id: str
    dataset_id: str | None = None
    evaluation_type: EvaluationType | str = "event"
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunResponse(BaseModel):
    evaluation_run: EvaluationRunRecord
    results: list[EvaluationResultRecord]
    summary: EvaluationSummaryArtifact
    failed_cases: list[FailedCaseRecord] = Field(default_factory=list)


class EvaluationRunListResponse(BaseModel):
    items: list[EvaluationRunRecord]
    total: int
    limit: int
    offset: int


class EvaluationResultListResponse(BaseModel):
    items: list[EvaluationResultRecord]
    total: int
    limit: int
    offset: int


class FailedCaseListResponse(BaseModel):
    items: list[FailedCaseRecord]
    total: int
    limit: int
    offset: int
