from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: str
    alert_id: str
    event_id: str
    video_id: str
    run_id: str
    alert_type: str
    title: str
    message: str
    level: str
    status: str
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    created_at: str
    track_id: int | None = None
    event_type: str | None = None
    frame_index: int | None = None
    timestamp_ms: int | None = None
    zone_id: str | None = None
    event_evidence_id: str | None = None
    snapshot_path: str | None = None


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int
    run_id: str | None = None
    status: str | None = None
    level: str | None = None


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str | None = Field(default=None)


Alert = AlertResponse
