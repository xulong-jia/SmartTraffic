from typing import Any

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class ModelRun(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "model_runs"

    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_version: Mapped[str | None] = mapped_column(String(128), index=True)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    artifact_paths: Mapped[dict[str, Any] | None] = mapped_column(JSON)
