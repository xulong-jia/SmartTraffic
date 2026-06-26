from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class Detection(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "detections"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id"), index=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    track_id: Mapped[str | None] = mapped_column(String(128), index=True)
