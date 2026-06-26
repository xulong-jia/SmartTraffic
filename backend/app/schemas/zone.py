from typing import Any

from pydantic import BaseModel, Field, field_validator


Point = list[float]
Polygon = list[Point]


class DirectionConfig(BaseModel):
    start_point: Point | None = None
    end_point: Point | None = None
    allowed_angle: float | None = None
    reverse_angle_threshold: float | None = None

    @field_validator("start_point", "end_point")
    @classmethod
    def validate_point(cls, value: Point | None) -> Point | None:
        return _validate_point(value)


class CountingLineConfig(BaseModel):
    start_point: Point | None = None
    end_point: Point | None = None
    in_direction: str = "any"
    enabled: bool = True

    @field_validator("start_point", "end_point")
    @classmethod
    def validate_point(cls, value: Point | None) -> Point | None:
        return _validate_point(value)


class ZoneBase(BaseModel):
    name: str
    zone_type: str
    polygon: Polygon
    direction: DirectionConfig | None = None
    counting_line: CountingLineConfig | None = None
    enabled: bool = True
    video_id: str | None = None
    camera_id: str | None = None
    version: int = 1

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: Polygon) -> Polygon:
        if len(value) < 3:
            raise ValueError("polygon must contain at least three points")
        return [_validate_point(point) for point in value]

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int) -> int:
        if int(value) < 1:
            raise ValueError("version must be at least 1")
        return int(value)


class ZoneCreate(ZoneBase):
    id: str | None = Field(default=None)


class ZoneUpdate(BaseModel):
    name: str | None = None
    zone_type: str | None = None
    polygon: Polygon | None = None
    direction: DirectionConfig | None = None
    counting_line: CountingLineConfig | None = None
    enabled: bool | None = None
    video_id: str | None = None
    camera_id: str | None = None
    version: int | None = None

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: Polygon | None) -> Polygon | None:
        if value is None:
            return None
        if len(value) < 3:
            raise ValueError("polygon must contain at least three points")
        return [_validate_point(point) for point in value]

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int | None) -> int | None:
        if value is not None and int(value) < 1:
            raise ValueError("version must be at least 1")
        return int(value) if value is not None else None


class ZoneResponse(ZoneBase):
    id: str


Zone = ZoneResponse


def _validate_point(value: Any) -> Point | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ValueError("point must contain exactly two coordinates")
    return [float(value[0]), float(value[1])]
