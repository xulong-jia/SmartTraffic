from pydantic import BaseModel


class Track(BaseModel):
    track_id: int
    class_name: str
    bbox: list[float]
    center: list[float]
    confidence: float | None = None
    state: str = "tentative"
