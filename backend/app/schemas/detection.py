from pydantic import BaseModel


class Detection(BaseModel):
    class_id: int | None = None
    class_name: str
    confidence: float
    bbox: list[float]


class FrameDetections(BaseModel):
    frame_index: int
    timestamp_ms: int | None = None
    detections: list[Detection]
