from typing import Any

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class Zone(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "zones"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    coordinates: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


class EventRule(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "event_rules"

    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="enabled", index=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
