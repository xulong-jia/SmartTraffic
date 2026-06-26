from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class ReviewComment(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "review_comments"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), index=True)
    author: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), default="open", index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
