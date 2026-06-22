from pydantic import BaseModel


class TrajectoryPoint(BaseModel):
    track_id: int
    frame_index: int
    timestamp_ms: int
    center_x: float
    center_y: float
