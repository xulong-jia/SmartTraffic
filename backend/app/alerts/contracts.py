from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any


ALERT_STATUSES = {"new", "acknowledged", "resolved", "ignored"}
SEVERITY_TO_ALERT_LEVEL = {
    "low": "info",
    "medium": "warning",
    "high": "critical",
}


def build_alert(
    *,
    event_id: str,
    run_id: str,
    video_id: str,
    event_type: str,
    alert_id: str | None = None,
    alert_type: str | None = None,
    title: str | None = None,
    message: str | None = None,
    level: str | None = None,
    status: str = "new",
    severity: str | None = "medium",
    track_id: int | None = None,
    frame_index: int | None = None,
    timestamp_ms: int | None = None,
    zone_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    effective_alert_type = alert_type or event_type
    effective_status = validate_alert_status(status)
    effective_level = level or severity_to_alert_level(severity)
    effective_alert_id = alert_id or generate_alert_id(
        run_id=run_id,
        event_id=event_id,
        alert_type=effective_alert_type,
    )

    return {
        "alert_id": effective_alert_id,
        "event_id": event_id,
        "run_id": run_id,
        "video_id": video_id,
        "track_id": track_id,
        "event_type": event_type,
        "alert_type": effective_alert_type,
        "title": title or _default_title(effective_alert_type),
        "message": message or _default_message(effective_alert_type),
        "level": effective_level,
        "status": effective_status,
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "zone_id": zone_id,
        "created_at": created_at or _utc_now_iso(),
    }


def generate_alert_id(*, run_id: str, event_id: str, alert_type: str) -> str:
    return "alert_" + _short_hash(
        {
            "run_id": run_id,
            "event_id": event_id,
            "alert_type": alert_type,
        }
    )


def severity_to_alert_level(severity: str | None) -> str:
    return SEVERITY_TO_ALERT_LEVEL.get(str(severity), "warning")


def validate_alert_status(status: str) -> str:
    if status not in ALERT_STATUSES:
        raise ValueError(f"unsupported alert status: {status}")
    return status


def _default_title(alert_type: str) -> str:
    return alert_type.replace("_", " ").capitalize()


def _default_message(alert_type: str) -> str:
    return f"{alert_type} event detected"


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
