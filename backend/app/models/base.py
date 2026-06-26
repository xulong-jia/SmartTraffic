from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StringIdMixin:
    id: Mapped[str] = mapped_column(String(64), primary_key=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
