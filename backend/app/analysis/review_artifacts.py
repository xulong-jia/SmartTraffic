from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from app.schemas.review import (
    EventReviewState,
    EventReviewStateItem,
    FalseNegativeEventRecord,
    REVIEW_ACTIONS,
    REVIEW_STATUSES,
    ReviewCommentRecord,
)


STAGE7B_SCHEMA_VERSION = "stage7b.v1"
REVIEW_ARTIFACTS = {
    "review_comments": "review_comments.jsonl",
    "event_review_state": "event_review_state.json",
    "false_negative_events": "false_negative_events.jsonl",
}

ACTION_AFTER_STATUS = {
    "confirm": "confirmed",
    "mark_false_positive": "false_positive",
    "ignore": "ignored",
    "resolve": "resolved",
}

ALLOWED_TRANSITIONS = {
    ("pending", "confirm"),
    ("pending", "mark_false_positive"),
    ("pending", "ignore"),
    ("confirmed", "resolve"),
    ("false_positive", "resolve"),
    ("ignored", "resolve"),
}


class ReviewArtifactError(ValueError):
    """Raised when a review artifact cannot be parsed or written."""


class ReviewStateTransitionError(ValueError):
    """Raised when a review action is not valid for the current state."""


def load_review_comments(result_dir: str | Path) -> list[dict[str, Any]]:
    return [
        ReviewCommentRecord.model_validate(row).model_dump()
        for row in _read_jsonl(_result_dir(result_dir) / REVIEW_ARTIFACTS["review_comments"])
    ]


def append_review_comment(
    result_dir: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    sequence = len(load_review_comments(run_dir)) + 1
    payload = dict(record)
    payload.setdefault("run_id", _run_id(run_dir, payload))
    payload.setdefault("alert_id", None)
    payload.setdefault("comment", "")
    payload.setdefault("reviewer", "local_reviewer")
    payload.setdefault("source", "review_center")
    payload.setdefault("created_at", _utc_now_iso())
    payload.setdefault("review_id", _stable_id("review", payload, sequence))
    normalized = ReviewCommentRecord.model_validate(payload).model_dump()
    _append_jsonl(run_dir / REVIEW_ARTIFACTS["review_comments"], normalized)
    _refresh_review_artifact_metadata(run_dir)
    return normalized


def load_event_review_state(
    result_dir: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    state_path = run_dir / REVIEW_ARTIFACTS["event_review_state"]
    if not state_path.is_file():
        return EventReviewState(
            run_id=run_id or _run_id(run_dir, {}),
            updated_at=None,
            events={},
        ).model_dump()
    payload = _read_json(state_path)
    return EventReviewState.model_validate(payload).model_dump()


def save_event_review_state(
    result_dir: str | Path,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    normalized = EventReviewState.model_validate(state).model_dump()
    _write_json_atomic(normalized, run_dir / REVIEW_ARTIFACTS["event_review_state"])
    _refresh_review_artifact_metadata(run_dir)
    return normalized


def current_event_review_status(
    result_dir: str | Path,
    event_id: str,
    *,
    run_id: str | None = None,
) -> str:
    state = load_event_review_state(result_dir, run_id=run_id)
    event_state = state["events"].get(event_id)
    if event_state is None:
        return "pending"
    return str(event_state.get("status") or "pending")


def apply_review_action(
    result_dir: str | Path,
    *,
    run_id: str,
    event_id: str,
    action: str,
    comment: str | None = None,
    reviewer: str | None = None,
    alert_id: str | None = None,
    source: str = "review_center",
) -> dict[str, Any]:
    if action == "add_false_negative":
        raise ReviewStateTransitionError(
            "add_false_negative creates false_negative records via append_false_negative"
        )
    if action not in REVIEW_ACTIONS:
        raise ReviewStateTransitionError(f"unsupported review action: {action}")

    before_status = current_event_review_status(
        result_dir,
        event_id,
        run_id=run_id,
    )
    after_status = _after_status(before_status, action)
    review_comment = append_review_comment(
        result_dir,
        {
            "run_id": run_id,
            "event_id": event_id,
            "alert_id": alert_id,
            "action": action,
            "before_status": before_status,
            "after_status": after_status,
            "comment": comment or "",
            "reviewer": reviewer or "local_reviewer",
            "source": source,
        },
    )
    state = load_event_review_state(result_dir, run_id=run_id)
    previous_event_state = state["events"].get(event_id, {})
    event_state = EventReviewStateItem(
        event_id=event_id,
        status=after_status,  # type: ignore[arg-type]
        last_action=action,  # type: ignore[arg-type]
        last_review_id=review_comment["review_id"],
        reviewer=review_comment["reviewer"],
        updated_at=review_comment["created_at"],
        comment_count=int(previous_event_state.get("comment_count") or 0) + 1,
    ).model_dump()
    state["schema_version"] = STAGE7B_SCHEMA_VERSION
    state["run_id"] = run_id
    state["updated_at"] = review_comment["created_at"]
    state["events"][event_id] = event_state
    save_event_review_state(result_dir, state)
    return {
        "run_id": run_id,
        "event_id": event_id,
        "status": after_status,
        "review_id": review_comment["review_id"],
        "updated_at": review_comment["created_at"],
    }


def append_false_negative(
    result_dir: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    sequence = len(load_false_negatives(run_dir)) + 1
    payload = dict(record)
    payload.setdefault("run_id", _run_id(run_dir, payload))
    payload.setdefault("zone_id", None)
    payload.setdefault("track_id", None)
    payload.setdefault("start_frame", None)
    payload.setdefault("end_frame", None)
    payload.setdefault("start_time_ms", None)
    payload.setdefault("end_time_ms", None)
    payload.setdefault("description", "")
    payload.setdefault("reviewer", "local_reviewer")
    payload.setdefault("created_at", _utc_now_iso())
    payload.setdefault("status", "false_negative")
    payload.setdefault("source", "review_center")
    payload.setdefault("false_negative_id", _stable_id("fn", payload, sequence))
    normalized = FalseNegativeEventRecord.model_validate(payload).model_dump()
    _append_jsonl(run_dir / REVIEW_ARTIFACTS["false_negative_events"], normalized)
    review_comment = append_review_comment(
        run_dir,
        {
            "run_id": normalized["run_id"],
            "event_id": normalized["false_negative_id"],
            "action": "add_false_negative",
            "before_status": None,
            "after_status": "false_negative",
            "comment": normalized["description"],
            "reviewer": normalized["reviewer"],
            "source": normalized["source"],
        },
    )
    state = load_event_review_state(run_dir, run_id=normalized["run_id"])
    state["schema_version"] = STAGE7B_SCHEMA_VERSION
    state["run_id"] = normalized["run_id"]
    state["updated_at"] = review_comment["created_at"]
    state["events"][normalized["false_negative_id"]] = EventReviewStateItem(
        event_id=normalized["false_negative_id"],
        status="false_negative",
        last_action="add_false_negative",
        last_review_id=review_comment["review_id"],
        reviewer=normalized["reviewer"],
        updated_at=review_comment["created_at"],
        comment_count=1,
    ).model_dump()
    save_event_review_state(run_dir, state)
    return normalized


def load_false_negatives(result_dir: str | Path) -> list[dict[str, Any]]:
    return [
        FalseNegativeEventRecord.model_validate(row).model_dump()
        for row in _read_jsonl(
            _result_dir(result_dir) / REVIEW_ARTIFACTS["false_negative_events"]
        )
    ]


def _after_status(before_status: str, action: str) -> str:
    if before_status not in REVIEW_STATUSES:
        raise ReviewStateTransitionError(f"unsupported review status: {before_status}")
    if action == "comment":
        return before_status
    if (before_status, action) not in ALLOWED_TRANSITIONS:
        raise ReviewStateTransitionError(
            f"cannot apply {action} from {before_status}"
        )
    return ACTION_AFTER_STATUS[action]


def _refresh_review_artifact_metadata(run_dir: Path) -> None:
    summaries = {
        key: _review_artifact_summary(run_dir, key, relative_path)
        for key, relative_path in REVIEW_ARTIFACTS.items()
    }
    _refresh_metadata(run_dir, summaries)
    _refresh_manifest(run_dir, summaries)
    _refresh_artifact_index(run_dir, summaries)


def _refresh_metadata(run_dir: Path, summaries: Mapping[str, dict[str, Any]]) -> None:
    metadata_path = run_dir / "metadata.json"
    metadata = _read_json(metadata_path) if metadata_path.is_file() else {}
    metadata.setdefault("run_id", _run_id(run_dir, metadata))
    artifacts = dict(metadata.get("artifacts", {}))
    artifacts.update(REVIEW_ARTIFACTS)
    metadata["artifacts"] = artifacts
    artifact_summary = dict(metadata.get("artifact_summary", {}))
    artifact_summary.update(
        {
            key: {
                "status": summary["status"],
                "path": summary["path"],
                "record_count": summary["record_count"],
            }
            for key, summary in summaries.items()
        }
    )
    metadata["artifact_summary"] = artifact_summary
    metadata["updated_at"] = _utc_now_iso()
    _write_json_atomic(metadata, metadata_path)


def _refresh_manifest(run_dir: Path, summaries: Mapping[str, dict[str, Any]]) -> None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = _read_json(manifest_path)
    artifacts = dict(manifest.get("artifacts", {}))
    artifacts.update(summaries)
    manifest["artifacts"] = artifacts
    manifest["updated_at"] = _utc_now_iso()
    _write_json_atomic(manifest, manifest_path)


def _refresh_artifact_index(
    run_dir: Path,
    summaries: Mapping[str, dict[str, Any]],
) -> None:
    artifact_index_path = run_dir / "artifact_index.json"
    if not artifact_index_path.is_file():
        return
    artifact_index = _read_json(artifact_index_path)
    artifacts = dict(artifact_index.get("artifacts", {}))
    for key, summary in summaries.items():
        if summary["status"] in {"available", "empty"}:
            artifacts[key] = summary["path"]
        else:
            artifacts.pop(key, None)
    artifact_index["artifacts"] = artifacts
    _write_json_atomic(artifact_index, artifact_index_path)


def _review_artifact_summary(
    run_dir: Path,
    key: str,
    relative_path: str,
) -> dict[str, Any]:
    path = run_dir / relative_path
    artifact_format = "json" if relative_path.endswith(".json") else "jsonl"
    try:
        record_count = _record_count(path, artifact_format, key)
        if not path.is_file():
            status = "missing"
        elif record_count == 0:
            status = "empty"
        else:
            status = "available"
    except (OSError, json.JSONDecodeError):
        status = "error"
        record_count = 0
    return {
        "status": status,
        "path": relative_path,
        "format": artifact_format,
        "record_count": record_count,
        "required": False,
    }


def _record_count(path: Path, artifact_format: str, key: str) -> int:
    if not path.is_file():
        return 0
    if artifact_format == "jsonl":
        with path.open(encoding="utf-8") as file:
            return sum(1 for line in file if line.strip())
    payload = _read_json(path)
    if key == "event_review_state" and isinstance(payload, Mapping):
        events = payload.get("events")
        return len(events) if isinstance(events, Mapping) else 0
    return 1


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ReviewArtifactError(
                    f"invalid JSONL in {path.name} at line {line_number}"
                ) from exc
    return rows


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
        file.write("\n")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ReviewArtifactError(f"invalid JSON in {path.name}") from exc
    if not isinstance(payload, dict):
        raise ReviewArtifactError(f"expected JSON object in {path.name}")
    return payload


def _write_json_atomic(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _stable_id(prefix: str, payload: Mapping[str, Any], sequence: int) -> str:
    material = dict(payload)
    material["_sequence"] = sequence
    serialized = json.dumps(material, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{sha256(serialized.encode('utf-8')).hexdigest()[:12]}"


def _run_id(run_dir: Path, payload: Mapping[str, Any]) -> str:
    value = payload.get("run_id")
    if value:
        return str(value)
    metadata_path = run_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = _read_json(metadata_path)
        metadata_run_id = metadata.get("run_id")
        if metadata_run_id:
            return str(metadata_run_id)
    return run_dir.name


def _result_dir(result_dir: str | Path) -> Path:
    return Path(result_dir)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
