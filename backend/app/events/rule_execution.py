from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any


RULE_EXECUTION_STATUSES = {"matched", "not_matched", "skipped", "error"}


def build_rule_execution(
    *,
    run_id: str,
    rule_id: str,
    execution_id: str | None = None,
    event_id: str | None = None,
    track_id: int | None = None,
    frame_index: int | None = None,
    status: str = "skipped",
    input_features: dict[str, Any] | None = None,
    output_result: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    validated_status = validate_rule_execution_status(status)
    effective_execution_id = execution_id or generate_rule_execution_id(
        run_id=run_id,
        rule_id=rule_id,
        track_id=track_id,
        frame_index=frame_index,
        status=validated_status,
    )

    return {
        "execution_id": effective_execution_id,
        "run_id": run_id,
        "rule_id": rule_id,
        "event_id": event_id,
        "track_id": track_id,
        "frame_index": frame_index,
        "status": validated_status,
        "input_features": input_features or {},
        "output_result": output_result or {},
        "created_at": created_at or _utc_now_iso(),
    }


def generate_rule_execution_id(
    *,
    run_id: str,
    rule_id: str,
    track_id: int | None = None,
    frame_index: int | None = None,
    status: str = "skipped",
) -> str:
    return "execution_" + _short_hash(
        {
            "run_id": run_id,
            "rule_id": rule_id,
            "track_id": track_id,
            "frame_index": frame_index,
            "status": status,
        }
    )


def validate_rule_execution_status(status: str) -> str:
    if status not in RULE_EXECUTION_STATUSES:
        raise ValueError(f"unsupported rule execution status: {status}")
    return status


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
