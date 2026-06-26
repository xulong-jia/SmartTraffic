"""Add camera realtime preview fields.

Revision ID: 0004_camera_realtime_preview
Revises: 0003_processing_task_progress
Create Date: 2026-06-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_camera_realtime_preview"
down_revision: str | None = "0003_processing_task_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = _column_names("cameras")
    with op.batch_alter_table("cameras") as batch:
        if "source_type" not in existing:
            batch.add_column(
                sa.Column(
                    "source_type",
                    sa.String(length=32),
                    nullable=False,
                    server_default="mock",
                )
            )
        if "enabled" not in existing:
            batch.add_column(
                sa.Column(
                    "enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        if "width" not in existing:
            batch.add_column(sa.Column("width", sa.Integer()))
        if "height" not in existing:
            batch.add_column(sa.Column("height", sa.Integer()))
        if "fps" not in existing:
            batch.add_column(sa.Column("fps", sa.Float()))

    existing_indexes = _index_names("cameras")
    if "ix_cameras_source_type" not in existing_indexes:
        op.create_index("ix_cameras_source_type", "cameras", ["source_type"])
    if "ix_cameras_enabled" not in existing_indexes:
        op.create_index("ix_cameras_enabled", "cameras", ["enabled"])


def downgrade() -> None:
    existing_indexes = _index_names("cameras")
    if "ix_cameras_enabled" in existing_indexes:
        op.drop_index("ix_cameras_enabled", table_name="cameras")
    if "ix_cameras_source_type" in existing_indexes:
        op.drop_index("ix_cameras_source_type", table_name="cameras")

    existing = _column_names("cameras")
    with op.batch_alter_table("cameras") as batch:
        if "fps" in existing:
            batch.drop_column("fps")
        if "height" in existing:
            batch.drop_column("height")
        if "width" in existing:
            batch.drop_column("width")
        if "enabled" in existing:
            batch.drop_column("enabled")
        if "source_type" in existing:
            batch.drop_column("source_type")


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}
