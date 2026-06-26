from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class Camera(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(512))
    stream_url: Mapped[str | None] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), default="mock", nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


class Video(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    camera_id: Mapped[str | None] = mapped_column(ForeignKey("cameras.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="uploaded", index=True)
    fps: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


class Frame(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "frames"

    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp_ms: Mapped[float | None] = mapped_column(Float)
    image_path: Mapped[str | None] = mapped_column(String(1024))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
