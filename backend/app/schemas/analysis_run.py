from typing import Any

from pydantic import BaseModel


class AnalysisRun(BaseModel):
    id: str
    video_id: str
    status: str
    result_dir: str
    artifact_index: dict[str, Any]
