from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class Track(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "tracks"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id"), index=True)
    track_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    class_name: Mapped[str | None] = mapped_column(String(128), index=True)
    start_frame: Mapped[int | None] = mapped_column(Integer)
    end_frame: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
