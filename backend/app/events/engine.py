from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.events.contracts import build_event
from app.events.dedup import build_event_dedup_key
from app.events.evidence import build_event_evidence
from app.events.rule_callbacks import DEFAULT_RULE_CALLBACKS
from app.events.rule_execution import build_rule_execution
from app.events.rules import EventRule, is_aggregate_rule


RuleCallback = Callable[
    [
        EventRule,
        dict[str, Any] | None,
        dict[str, Any],
        list[dict[str, Any]] | None,
        dict[str, Any],
    ],
    dict[str, Any],
]


class EventEngine:
    """Minimal event rule execution framework.

    This class only coordinates configurable rule callbacks and common filters.
    Concrete traffic-event rules are intentionally left to later steps.
    """

    def __init__(
        self,
        *,
        run_id: str,
        video_id: str,
        record_not_matched: bool = False,
        rule_callbacks: dict[str, RuleCallback] | None = None,
    ) -> None:
        self.run_id = run_id
        self.video_id = video_id
        self.record_not_matched = bool(record_not_matched)
        self.default_rule_callbacks = dict(DEFAULT_RULE_CALLBACKS)
        self.rule_callbacks = dict(rule_callbacks or {})
        self.reset()

    def update(
        self,
        frame_result: Mapping[str, Any],
        rules: Sequence[EventRule | dict[str, Any]] | None = None,
        zones: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        frame_index = frame_result.get("frame_index")
        timestamp_ms = frame_result.get("timestamp_ms")
        result = {
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "events": [],
            "event_evidence": [],
            "rule_executions": [],
        }
        trajectory_points = list(frame_result.get("trajectory_points", []) or [])
        event_rules = [_normalize_rule(rule) for rule in rules or []]
        if not event_rules:
            return result

        track_rules = [rule for rule in event_rules if not is_aggregate_rule(rule)]
        aggregate_rules = [rule for rule in event_rules if is_aggregate_rule(rule)]

        frame_payload = dict(frame_result)
        frame_payload["trajectory_points"] = [dict(point) for point in trajectory_points]

        for trajectory_point in frame_payload["trajectory_points"]:
            for rule in track_rules:
                self._evaluate_rule_for_point(
                    result=result,
                    rule=rule,
                    trajectory_point=trajectory_point,
                    frame_result=frame_payload,
                    zones=zones,
                )
        for rule in aggregate_rules:
            self._evaluate_aggregate_rule(
                result=result,
                rule=rule,
                frame_result=frame_payload,
                zones=zones,
            )
        return result

    def evaluate(
        self,
        trajectory_frames: Sequence[Mapping[str, Any]],
        rules: Sequence[EventRule | dict[str, Any]] | None = None,
        zones: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        event_evidence: list[dict[str, Any]] = []
        rule_executions: list[dict[str, Any]] = []

        for frame_result in trajectory_frames:
            frame_output = self.update(frame_result, rules=rules, zones=zones)
            events.extend(frame_output["events"])
            event_evidence.extend(frame_output["event_evidence"])
            rule_executions.extend(frame_output["rule_executions"])

        return {
            "events": events,
            "event_evidence": event_evidence,
            "rule_executions": rule_executions,
            "summary": self.get_summary(),
        }

    def reset(self) -> None:
        self._callback_state: dict[str, Any] = {}
        self._last_event_time_by_key: dict[str, float] = {}
        self._emitted_event_keys: set[str] = set()
        self._total_events = 0
        self._total_event_evidence = 0
        self._total_rule_executions = 0
        self._per_event_type_counts: dict[str, int] = {}
        self._per_rule_status_counts: dict[str, int] = {}
        self._unique_track_ids: set[Any] = set()

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "total_event_evidence": self._total_event_evidence,
            "total_rule_executions": self._total_rule_executions,
            "per_event_type_counts": dict(sorted(self._per_event_type_counts.items())),
            "per_rule_status_counts": dict(sorted(self._per_rule_status_counts.items())),
            "unique_track_ids": len(self._unique_track_ids),
        }

    def _evaluate_rule_for_point(
        self,
        *,
        result: dict[str, Any],
        rule: EventRule,
        trajectory_point: dict[str, Any],
        frame_result: dict[str, Any],
        zones: list[dict[str, Any]] | None,
    ) -> None:
        if not rule.enabled:
            self._append_skipped(result, rule, trajectory_point, frame_result, "rule_disabled")
            return

        if not self._target_class_matches(rule, trajectory_point):
            self._append_skipped(
                result,
                rule,
                trajectory_point,
                frame_result,
                "target_class_filtered",
            )
            return

        if _track_length(trajectory_point) < rule.min_track_length:
            self._append_skipped(
                result,
                rule,
                trajectory_point,
                frame_result,
                "min_track_length_not_met",
            )
            return

        dedup_key = self._dedup_key(rule, trajectory_point)
        if self._is_in_cooldown(rule, frame_result, dedup_key):
            self._append_skipped(result, rule, trajectory_point, frame_result, "cooldown")
            return

        callback = self._rule_callback(rule, zones)
        if callback is None:
            self._append_skipped(
                result,
                rule,
                trajectory_point,
                frame_result,
                "rule_callback_missing",
            )
            return

        try:
            callback_output = callback(
                rule,
                trajectory_point,
                frame_result,
                zones,
                self._engine_state(),
            )
        except Exception as exc:
            self._append_execution(
                result,
                rule=rule,
                trajectory_point=trajectory_point,
                frame_result=frame_result,
                status="error",
                input_features=_input_features(trajectory_point),
                output_result={"reason": "rule_error", "error": str(exc)},
            )
            return

        matched = bool(callback_output.get("matched"))
        if not matched:
            if self.record_not_matched:
                self._append_execution(
                    result,
                    rule=rule,
                    trajectory_point=trajectory_point,
                    frame_result=frame_result,
                    status="not_matched",
                    input_features=callback_output.get("input_features")
                    or _input_features(trajectory_point),
                    output_result=_callback_output_result(
                        callback_output,
                        matched=False,
                        default_reason="not_matched",
                    ),
                )
            return

        event = self._build_matched_event(rule, trajectory_point, frame_result, callback_output)
        evidence = self._build_matched_evidence(
            event,
            trajectory_point,
            frame_result,
            callback_output,
        )
        result["events"].append(event)
        result["event_evidence"].extend(evidence)
        self._append_execution(
            result,
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            status="matched",
            event_id=event["event_id"],
            input_features=callback_output.get("input_features")
            or _input_features(trajectory_point),
            output_result=_callback_output_result(
                callback_output,
                matched=True,
                default_reason="matched",
            ),
        )
        marker = _cooldown_marker(frame_result)
        if marker is not None:
            self._last_event_time_by_key[dedup_key] = marker
        self._emitted_event_keys.add(dedup_key)
        self._record_event(event, evidence)

    def _evaluate_aggregate_rule(
        self,
        *,
        result: dict[str, Any],
        rule: EventRule,
        frame_result: dict[str, Any],
        zones: list[dict[str, Any]] | None,
    ) -> None:
        if not rule.enabled:
            self._append_skipped(result, rule, None, frame_result, "rule_disabled")
            return

        # Aggregate rules own class and track-length filtering because they
        # evaluate the full frame rather than a single trajectory point.
        dedup_key = self._dedup_key(rule, None)
        if self._is_in_cooldown(rule, frame_result, dedup_key):
            self._append_skipped(result, rule, None, frame_result, "cooldown")
            return

        callback = self._rule_callback(rule, zones)
        if callback is None:
            self._append_skipped(result, rule, None, frame_result, "rule_callback_missing")
            return

        try:
            callback_output = callback(
                rule,
                None,
                frame_result,
                zones,
                self._engine_state(),
            )
        except Exception as exc:
            self._append_execution(
                result,
                rule=rule,
                trajectory_point=None,
                frame_result=frame_result,
                status="error",
                input_features=_input_features(None),
                output_result={"reason": "rule_error", "error": str(exc)},
            )
            return

        matched = bool(callback_output.get("matched"))
        if not matched:
            if self.record_not_matched:
                self._append_execution(
                    result,
                    rule=rule,
                    trajectory_point=None,
                    frame_result=frame_result,
                    status="not_matched",
                    input_features=callback_output.get("input_features")
                    or _input_features(None),
                    output_result=_callback_output_result(
                        callback_output,
                        matched=False,
                        default_reason="not_matched",
                    ),
                )
            return

        event = self._build_matched_event(rule, None, frame_result, callback_output)
        evidence = self._build_matched_evidence(
            event,
            None,
            frame_result,
            callback_output,
        )
        result["events"].append(event)
        result["event_evidence"].extend(evidence)
        self._append_execution(
            result,
            rule=rule,
            trajectory_point=None,
            frame_result=frame_result,
            status="matched",
            event_id=event["event_id"],
            input_features=callback_output.get("input_features")
            or _input_features(None),
            output_result=_callback_output_result(
                callback_output,
                matched=True,
                default_reason="matched",
            ),
        )
        marker = _cooldown_marker(frame_result)
        if marker is not None:
            self._last_event_time_by_key[dedup_key] = marker
        self._emitted_event_keys.add(dedup_key)
        self._record_event(event, evidence)

    def _rule_callback(
        self,
        rule: EventRule,
        zones: list[dict[str, Any]] | None,
    ) -> RuleCallback | None:
        callback = self.rule_callbacks.get(rule.rule_id) or self.rule_callbacks.get(
            rule.event_type
        )
        if callback is not None:
            return callback
        if zones is None:
            return None
        return self.default_rule_callbacks.get(rule.event_type)

    def _append_skipped(
        self,
        result: dict[str, Any],
        rule: EventRule,
        trajectory_point: dict[str, Any] | None,
        frame_result: dict[str, Any],
        reason: str,
    ) -> None:
        self._append_execution(
            result,
            rule=rule,
            trajectory_point=trajectory_point,
            frame_result=frame_result,
            status="skipped",
            input_features=_input_features(trajectory_point),
            output_result={"reason": reason},
        )

    def _append_execution(
        self,
        result: dict[str, Any],
        *,
        rule: EventRule,
        trajectory_point: dict[str, Any] | None,
        frame_result: dict[str, Any],
        status: str,
        event_id: str | None = None,
        input_features: dict[str, Any] | None = None,
        output_result: dict[str, Any] | None = None,
    ) -> None:
        execution = build_rule_execution(
            run_id=self.run_id,
            rule_id=rule.rule_id,
            event_id=event_id,
            track_id=_track_id(trajectory_point),
            frame_index=frame_result.get("frame_index"),
            status=status,
            input_features=input_features,
            output_result=output_result,
        )
        result["rule_executions"].append(execution)
        self._record_execution(execution)

    def _build_matched_event(
        self,
        rule: EventRule,
        trajectory_point: dict[str, Any] | None,
        frame_result: dict[str, Any],
        callback_output: dict[str, Any],
    ) -> dict[str, Any]:
        raw_event = dict(callback_output.get("event") or {})
        return build_event(
            event_id=raw_event.get("event_id"),
            run_id=raw_event.get("run_id", self.run_id),
            video_id=raw_event.get("video_id", self.video_id),
            event_type=raw_event.get("event_type", rule.event_type),
            severity=raw_event.get("severity", rule.severity),
            track_id=raw_event.get("track_id", _track_id(trajectory_point)),
            class_name=raw_event.get(
                "class_name",
                trajectory_point.get("class_name") if trajectory_point is not None else None,
            ),
            zone_id=raw_event.get("zone_id", rule.zone_id),
            rule_id=raw_event.get("rule_id", rule.rule_id),
            start_frame=raw_event.get("start_frame", frame_result.get("frame_index")),
            end_frame=raw_event.get("end_frame", frame_result.get("frame_index")),
            start_time_ms=raw_event.get("start_time_ms", frame_result.get("timestamp_ms")),
            end_time_ms=raw_event.get("end_time_ms", frame_result.get("timestamp_ms")),
            confidence=raw_event.get("confidence", 1.0),
            status=raw_event.get("status", "pending"),
            evidence=raw_event.get("evidence", {}),
            created_at=raw_event.get("created_at"),
        )

    def _build_matched_evidence(
        self,
        event: dict[str, Any],
        trajectory_point: dict[str, Any] | None,
        frame_result: dict[str, Any],
        callback_output: dict[str, Any],
    ) -> list[dict[str, Any]]:
        evidence_values = callback_output.get("evidence") or []
        if isinstance(evidence_values, Mapping):
            evidence_values = [evidence_values]

        evidence: list[dict[str, Any]] = []
        for item in evidence_values:
            raw_evidence = dict(item)
            evidence.append(
                build_event_evidence(
                    evidence_id=raw_evidence.get("evidence_id"),
                    event_id=raw_evidence.get("event_id", event["event_id"]),
                    run_id=raw_evidence.get("run_id", self.run_id),
                    video_id=raw_evidence.get("video_id", self.video_id),
                    track_id=raw_evidence.get("track_id", _track_id(trajectory_point)),
                    frame_index=raw_evidence.get(
                        "frame_index",
                        frame_result.get("frame_index"),
                    ),
                    timestamp_ms=raw_evidence.get(
                        "timestamp_ms",
                        frame_result.get("timestamp_ms"),
                    ),
                    evidence_type=raw_evidence.get("evidence_type", "rule"),
                    evidence_json=raw_evidence.get("evidence_json", {}),
                    snapshot_path=raw_evidence.get("snapshot_path"),
                    created_at=raw_evidence.get("created_at"),
                )
            )
        return evidence

    def _target_class_matches(
        self,
        rule: EventRule,
        trajectory_point: dict[str, Any],
    ) -> bool:
        if not rule.target_classes:
            return True
        return str(trajectory_point.get("class_name")) in rule.target_classes

    def _dedup_key(self, rule: EventRule, trajectory_point: dict[str, Any] | None) -> str:
        return build_event_dedup_key(
            run_id=self.run_id,
            event_type=rule.event_type,
            track_id=_track_id(trajectory_point),
            zone_id=rule.zone_id,
            rule_id=rule.rule_id,
        )

    def _is_in_cooldown(
        self,
        rule: EventRule,
        frame_result: dict[str, Any],
        dedup_key: str,
    ) -> bool:
        if rule.cooldown_seconds <= 0:
            return False
        current_marker = _cooldown_marker(frame_result)
        if current_marker is None:
            return False
        last_marker = self._last_event_time_by_key.get(dedup_key)
        if last_marker is None:
            return False
        threshold = (
            rule.cooldown_seconds * 1000
            if frame_result.get("timestamp_ms") is not None
            else rule.cooldown_seconds
        )
        return current_marker - last_marker < threshold

    def _engine_state(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "video_id": self.video_id,
            "summary": self.get_summary(),
            "state": self._callback_state,
        }

    def _record_event(
        self,
        event: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> None:
        self._total_events += 1
        self._total_event_evidence += len(evidence)
        event_type = str(event["event_type"])
        self._per_event_type_counts[event_type] = (
            self._per_event_type_counts.get(event_type, 0) + 1
        )
        track_id = event.get("track_id")
        if track_id is not None:
            self._unique_track_ids.add(track_id)

    def _record_execution(self, execution: dict[str, Any]) -> None:
        self._total_rule_executions += 1
        status = str(execution["status"])
        self._per_rule_status_counts[status] = (
            self._per_rule_status_counts.get(status, 0) + 1
        )


def _normalize_rule(rule: EventRule | dict[str, Any]) -> EventRule:
    if isinstance(rule, EventRule):
        return rule
    if isinstance(rule, dict):
        return EventRule.from_dict(rule)
    raise ValueError("rule must be an EventRule or dict")


def _track_id(trajectory_point: Mapping[str, Any] | None) -> int | None:
    if trajectory_point is None:
        return None
    track_id = trajectory_point.get("track_id")
    if track_id is None:
        return None
    return int(track_id)


def _track_length(trajectory_point: Mapping[str, Any]) -> int:
    track_length = trajectory_point.get("track_length")
    if track_length is None:
        return 0
    return int(track_length)


def _input_features(trajectory_point: Mapping[str, Any] | None) -> dict[str, Any]:
    if trajectory_point is None:
        return {
            "track_id": None,
            "class_name": None,
            "track_length": None,
        }
    return {
        "track_id": trajectory_point.get("track_id"),
        "class_name": trajectory_point.get("class_name"),
        "track_length": trajectory_point.get("track_length"),
    }


def _callback_output_result(
    callback_output: Mapping[str, Any],
    *,
    matched: bool,
    default_reason: str,
) -> dict[str, Any]:
    output_result = dict(callback_output.get("output_result") or {})
    output_result.setdefault("matched", matched)
    output_result.setdefault("reason", callback_output.get("reason", default_reason))
    return output_result


def _cooldown_marker(frame_result: Mapping[str, Any]) -> float | None:
    timestamp_ms = frame_result.get("timestamp_ms")
    if timestamp_ms is not None:
        return float(timestamp_ms)
    frame_index = frame_result.get("frame_index")
    if frame_index is not None:
        return float(frame_index)
    return None
