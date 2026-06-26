from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class TrajectoryPoint(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "trajectory_points"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id"), index=True)
    track_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp_ms: Mapped[float | None] = mapped_column(Float)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str | None] = mapped_column(String(64))
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON)
