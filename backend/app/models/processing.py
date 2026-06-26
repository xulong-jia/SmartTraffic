from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class ProcessingTask(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "processing_tasks"

    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    mode: Mapped[str | None] = mapped_column(String(128), index=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
