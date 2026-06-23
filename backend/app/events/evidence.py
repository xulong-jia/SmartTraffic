from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


EVIDENCE_TYPES = {
    "trajectory",
    "zone",
    "speed",
    "direction",
    "dwell",
    "rule",
    "line_crossing",
    "zone_statistics",
}


def build_evidence(**values) -> dict:
    return dict(values)


def build_event_evidence(
    *,
    event_id: str,
    run_id: str,
    video_id: str,
    evidence_type: str,
    evidence_id: str | None = None,
    track_id: int | None = None,
    frame_index: int | None = None,
    timestamp_ms: int | None = None,
    event_type: str | None = None,
    zone_id: str | None = None,
    rule_id: str | None = None,
    evidence_json: dict[str, Any] | None = None,
    snapshot_path: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    validated_evidence_type = validate_evidence_type(evidence_type)
    if snapshot_path is not None and Path(snapshot_path).is_absolute():
        raise ValueError("snapshot_path must not be an absolute path")

    effective_evidence_id = evidence_id or generate_evidence_id(
        event_id=event_id,
        evidence_type=validated_evidence_type,
        frame_index=frame_index,
        track_id=track_id,
    )

    return {
        "evidence_id": effective_evidence_id,
        "event_id": event_id,
        "run_id": run_id,
        "video_id": video_id,
        "track_id": track_id,
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "event_type": event_type,
        "zone_id": zone_id,
        "rule_id": rule_id,
        "evidence_type": validated_evidence_type,
        "evidence_json": evidence_json or {},
        "snapshot_path": snapshot_path,
        "created_at": created_at or _utc_now_iso(),
    }


def generate_evidence_id(
    *,
    event_id: str,
    evidence_type: str,
    frame_index: int | None = None,
    track_id: int | None = None,
) -> str:
    return "evidence_" + _short_hash(
        {
            "event_id": event_id,
            "evidence_type": evidence_type,
            "frame_index": frame_index,
            "track_id": track_id,
        }
    )


def validate_evidence_type(evidence_type: str) -> str:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unsupported evidence type: {evidence_type}")
    return evidence_type


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
