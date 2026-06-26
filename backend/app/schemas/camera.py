from typing import Any

from pydantic import BaseModel, Field


CameraSourceType = str


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str | None = None
    source_type: CameraSourceType = "mock"
    stream_url: str | None = None
    enabled: bool = True
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = None
    source_type: CameraSourceType | None = None
    stream_url: str | None = None
    enabled: bool | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    metadata: dict[str, Any] | None = None


class CameraResponse(BaseModel):
    id: str
    name: str
    location: str | None = None
    source_type: CameraSourceType
    masked_stream_url: str | None = None
    enabled: bool
    status: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class CameraDeleteResponse(BaseModel):
    deleted: bool
    camera_id: str
