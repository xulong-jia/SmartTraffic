from typing import Any

from pydantic import BaseModel


class TrafficEvent(BaseModel):
    event_type: str
    severity: str
    track_id: int | None = None
    zone_id: str | None = None
    evidence: dict[str, Any]
