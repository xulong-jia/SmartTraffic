"""Add processing task progress fields.

Revision ID: 0003_processing_task_progress
Revises: 0002_core_database_models
Create Date: 2026-06-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_processing_task_progress"
down_revision: str | None = "0002_core_database_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = _column_names()
    with op.batch_alter_table("processing_tasks") as batch:
        if "progress" not in existing:
            batch.add_column(
                sa.Column(
                    "progress",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "started_at" not in existing:
            batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True)))
        if "finished_at" not in existing:
            batch.add_column(sa.Column("finished_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    existing = _column_names()
    with op.batch_alter_table("processing_tasks") as batch:
        if "finished_at" in existing:
            batch.drop_column("finished_at")
        if "started_at" in existing:
            batch.drop_column("started_at")
        if "progress" in existing:
            batch.drop_column("progress")


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("processing_tasks")}
