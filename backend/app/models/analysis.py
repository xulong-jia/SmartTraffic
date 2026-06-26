from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class TrafficAnalysisRun(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "traffic_analysis_runs"

    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="created", index=True)
    result_dir: Mapped[str | None] = mapped_column(String(1024))
    artifact_index: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class FlowCount(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "flow_counts"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), index=True)
    line_id: Mapped[str | None] = mapped_column(String(128), index=True)
    class_name: Mapped[str | None] = mapped_column(String(128), index=True)
    direction: Mapped[str | None] = mapped_column(String(64), index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ZoneStatistic(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "zone_statistics"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
