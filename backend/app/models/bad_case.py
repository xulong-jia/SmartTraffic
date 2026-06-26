from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class BadCase(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "bad_cases"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="open", index=True)
    severity: Mapped[str | None] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
