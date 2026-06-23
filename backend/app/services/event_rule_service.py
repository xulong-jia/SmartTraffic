from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from app.schemas.event_rule import EventRuleCreate, EventRuleResponse, EventRuleUpdate
from app.services.zone_service import zone_service


class EventRuleService:
    def __init__(self) -> None:
        self._rules: dict[str, dict[str, Any]] = {}

    def create_rule(
        self,
        payload: EventRuleCreate | Mapping[str, Any],
    ) -> dict[str, Any]:
        values = _dump_payload(payload)
        rule_id = str(values.get("id") or f"rule_{uuid4().hex[:12]}")
        if rule_id in self._rules:
            raise ValueError(f"event rule already exists: {rule_id}")
        values["id"] = rule_id
        rule = EventRuleResponse(**values).model_dump()
        self._rules[rule_id] = rule
        return dict(rule)

    def list_rules(
        self,
        *,
        event_type: str | None = None,
        enabled: bool | None = None,
        zone_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rules = []
        for rule in self._rules.values():
            if event_type is not None and rule.get("event_type") != event_type:
                continue
            if enabled is not None and bool(rule.get("enabled", True)) is not enabled:
                continue
            if zone_id is not None and rule.get("zone_id") != zone_id:
                continue
            rules.append(dict(rule))
        return rules

    def get_rule(self, rule_id: str) -> dict[str, Any]:
        if rule_id not in self._rules:
            raise KeyError(rule_id)
        return dict(self._rules[rule_id])

    def update_rule(
        self,
        rule_id: str,
        payload: EventRuleUpdate | Mapping[str, Any],
    ) -> dict[str, Any]:
        current = self.get_rule(rule_id)
        updates = _dump_payload(payload, exclude_unset=True)
        updates.pop("id", None)
        current.update(updates)
        current["id"] = rule_id
        rule = EventRuleResponse(**current).model_dump()
        self._rules[rule_id] = rule
        return dict(rule)

    def delete_rule(self, rule_id: str) -> None:
        if rule_id not in self._rules:
            raise KeyError(rule_id)
        del self._rules[rule_id]

    def build_event_engine_rules(
        self,
        *,
        rules: list[dict[str, Any]] | None = None,
        zones: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        source_rules = (
            [dict(rule) for rule in rules]
            if rules is not None
            else self.list_rules(enabled=True)
        )
        zones_by_id = {
            str(zone.get("zone_id") or zone.get("id")): zone
            for zone in zones or []
            if zone.get("zone_id") is not None or zone.get("id") is not None
        }
        return [_to_event_engine_rule(rule, zones_by_id) for rule in source_rules]

    def build_event_engine_config(
        self,
        *,
        video_id: str | None = None,
        zones: list[dict[str, Any]] | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        event_zones = zone_service.build_event_engine_zones(
            video_id=video_id,
            zones=zones,
        )
        source_rules = rules
        if source_rules is None:
            source_rules = self.list_rules(enabled=True)
            if video_id is not None:
                source_rules = _filter_rules_for_zones(source_rules, event_zones)
        event_rules = self.build_event_engine_rules(
            rules=source_rules,
            zones=event_zones,
        )
        return {"zones": event_zones, "event_rules": event_rules}

    def clear(self) -> None:
        self._rules.clear()


def _to_event_engine_rule(
    rule: Mapping[str, Any],
    zones_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = dict(rule)
    rule_id = normalized.get("rule_id") or normalized.get("id")
    normalized["id"] = str(normalized.get("id") or rule_id)
    normalized["rule_id"] = str(rule_id)
    normalized["parameters"] = _build_parameters(normalized, zones_by_id)
    return normalized


def _build_parameters(
    rule: Mapping[str, Any],
    zones_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    parameters = dict(rule.get("parameters") or {})
    event_type = str(rule.get("event_type"))
    zone = zones_by_id.get(str(rule.get("zone_id")))

    if event_type == "congestion":
        parameters.setdefault("rule_mode", "aggregate")

    if zone is not None and event_type == "wrong_way_driving":
        direction = zone.get("direction") or {}
        allowed_angle = direction.get("allowed_angle")
        reverse_angle_threshold = direction.get("reverse_angle_threshold")
        if allowed_angle is not None:
            parameters.setdefault("allowed_angle", allowed_angle)
        if reverse_angle_threshold is not None:
            parameters.setdefault("reverse_angle_threshold", reverse_angle_threshold)
            parameters.setdefault(
                "angle_tolerance",
                max(0.0, 180.0 - float(reverse_angle_threshold)),
            )

    if zone is not None and event_type == "flow_counting":
        counting_line = zone.get("counting_line") or {}
        if counting_line.get("enabled", True):
            start_point = counting_line.get("start_point")
            end_point = counting_line.get("end_point")
            if start_point is not None and end_point is not None:
                parameters.setdefault("line", [start_point, end_point])
                parameters.setdefault("line_id", str(rule.get("zone_id")))
            if counting_line.get("in_direction") is not None:
                parameters.setdefault("direction", counting_line["in_direction"])

    return parameters


def _filter_rules_for_zones(
    rules: list[dict[str, Any]],
    zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    zone_ids = {
        str(zone.get("zone_id") or zone.get("id"))
        for zone in zones
        if zone.get("zone_id") is not None or zone.get("id") is not None
    }
    return [
        rule
        for rule in rules
        if rule.get("zone_id") is None or str(rule.get("zone_id")) in zone_ids
    ]


def _dump_payload(
    payload: EventRuleCreate | EventRuleUpdate | Mapping[str, Any],
    *,
    exclude_unset: bool = False,
) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_none=True, exclude_unset=exclude_unset)
    return {key: value for key, value in dict(payload).items() if value is not None}


event_rule_service = EventRuleService()
