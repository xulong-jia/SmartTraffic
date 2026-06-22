from dataclasses import dataclass, field
from typing import Any

from app.events.contracts import validate_event_severity


SUPPORTED_EVENT_TYPES = [
    "wrong_way_driving",
    "illegal_parking",
    "danger_zone_intrusion",
    "pedestrian_in_vehicle_lane",
    "congestion",
    "flow_counting",
]


@dataclass
class EventRule:
    rule_id: str
    name: str
    event_type: str
    enabled: bool = True
    severity: str = "medium"
    target_classes: tuple[str, ...] = ()
    zone_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    cooldown_seconds: float = 0.0
    min_track_length: int = 1

    def __post_init__(self) -> None:
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported event type: {self.event_type}")
        self.enabled = bool(self.enabled)
        self.severity = validate_event_severity(self.severity)
        self.target_classes = _normalize_target_classes(self.target_classes)
        if not isinstance(self.parameters, dict):
            raise ValueError("parameters must be a dict")
        self.parameters = dict(self.parameters)
        self.cooldown_seconds = float(self.cooldown_seconds)
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.min_track_length = int(self.min_track_length)
        if self.min_track_length < 1:
            raise ValueError("min_track_length must be at least 1")

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "EventRule":
        if not isinstance(values, dict):
            raise ValueError("EventRule values must be a dict")
        return cls(**values)


def _normalize_target_classes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)
