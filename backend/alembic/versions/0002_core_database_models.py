"""Core database models.

Revision ID: 0002_core_database_models
Revises: 0001_db_foundation
Create Date: 2026-06-26
"""

from collections.abc import Sequence

from alembic import op

from app.db.base import Base
import app.models  # noqa: F401


revision: str = "0002_core_database_models"
down_revision: str | None = "0001_db_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
