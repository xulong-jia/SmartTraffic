from typing import Any

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import StringIdMixin, TimestampMixin


class EvaluationDataset(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dataset_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class EvaluationResult(StringIdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_results"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("evaluation_datasets.id"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("traffic_analysis_runs.id"), nullable=False, index=True)
    evaluation_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="completed", index=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
