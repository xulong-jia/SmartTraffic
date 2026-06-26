from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class Event(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "events"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id"), index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("event_rules.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="new", index=True)
    severity: Mapped[str | None] = mapped_column(String(64), index=True)
    frame_index: Mapped[int | None] = mapped_column(Integer, index=True)
    timestamp_ms: Mapped[float | None] = mapped_column(Float)
    track_id: Mapped[str | None] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class EventEvidence(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "event_evidence"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("traffic_analysis_runs.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    artifact_path: Mapped[str | None] = mapped_column(String(1024))


class RuleExecution(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "rule_executions"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("event_rules.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
