from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.events.rules import SUPPORTED_EVENT_TYPES

EventRuleSeverity = Literal["low", "medium", "high"]


class EventRuleBase(BaseModel):
    name: str
    event_type: str
    enabled: bool = True
    zone_id: str | None = None
    target_classes: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    cooldown_seconds: float = 0.0
    severity: EventRuleSeverity = "medium"
    version: int = 1
    min_track_length: int = 1

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported event type: {value}")
        return value

    @field_validator("cooldown_seconds")
    @classmethod
    def validate_cooldown_seconds(cls, value: float) -> float:
        if value < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        return float(value)

    @field_validator("version", "min_track_length")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if int(value) < 1:
            raise ValueError("value must be at least 1")
        return int(value)


class EventRuleCreate(EventRuleBase):
    id: str | None = None


class EventRuleUpdate(BaseModel):
    name: str | None = None
    event_type: str | None = None
    enabled: bool | None = None
    zone_id: str | None = None
    target_classes: list[str] | None = None
    parameters: dict[str, Any] | None = None
    cooldown_seconds: float | None = None
    severity: EventRuleSeverity | None = None
    version: int | None = None
    min_track_length: int | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str | None) -> str | None:
        if value is not None and value not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported event type: {value}")
        return value

    @field_validator("cooldown_seconds")
    @classmethod
    def validate_cooldown_seconds(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        return value

    @field_validator("version", "min_track_length")
    @classmethod
    def validate_positive_int(cls, value: int | None) -> int | None:
        if value is not None and int(value) < 1:
            raise ValueError("value must be at least 1")
        return int(value) if value is not None else None


class EventRuleResponse(EventRuleBase):
    id: str
