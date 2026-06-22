from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any


EVENT_SEVERITIES = {"low", "medium", "high"}
EVENT_STATUSES = {
    "pending",
    "confirmed",
    "false_positive",
    "false_negative",
    "ignored",
    "resolved",
}


def build_event(
    *,
    run_id: str,
    video_id: str,
    event_type: str,
    event_id: str | None = None,
    severity: str = "medium",
    track_id: int | None = None,
    class_name: str | None = None,
    zone_id: str | None = None,
    rule_id: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    confidence: float = 1.0,
    status: str = "pending",
    evidence: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    validated_severity = validate_event_severity(severity)
    validated_status = validate_event_status(status)
    effective_event_id = event_id or generate_event_id(
        run_id=run_id,
        event_type=event_type,
        track_id=track_id,
        zone_id=zone_id,
        rule_id=rule_id,
        start_frame=start_frame,
        end_frame=end_frame,
    )

    return {
        "event_id": effective_event_id,
        "run_id": run_id,
        "video_id": video_id,
        "event_type": event_type,
        "severity": validated_severity,
        "track_id": track_id,
        "class_name": class_name,
        "zone_id": zone_id,
        "rule_id": rule_id,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_time_ms": start_time_ms,
        "end_time_ms": end_time_ms,
        "confidence": float(confidence),
        "status": validated_status,
        "evidence": evidence or {},
        "created_at": created_at or _utc_now_iso(),
    }


def generate_event_id(
    *,
    run_id: str,
    event_type: str,
    track_id: int | None = None,
    zone_id: str | None = None,
    rule_id: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> str:
    return "event_" + _short_hash(
        {
            "run_id": run_id,
            "event_type": event_type,
            "track_id": track_id,
            "zone_id": zone_id,
            "rule_id": rule_id,
            "start_frame": start_frame,
            "end_frame": end_frame,
        }
    )


def validate_event_severity(severity: str) -> str:
    if severity not in EVENT_SEVERITIES:
        raise ValueError(f"unsupported event severity: {severity}")
    return severity


def validate_event_status(status: str) -> str:
    if status not in EVENT_STATUSES:
        raise ValueError(f"unsupported event status: {status}")
    return status


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
