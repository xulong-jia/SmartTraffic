from collections.abc import Mapping
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from app.schemas.bad_case import (
    BadCaseRecord,
    BadCaseSummary,
    BadCaseUpdateAuditRecord,
)


STAGE8B_SCHEMA_VERSION = "stage8b.v1"
BAD_CASE_ARTIFACTS = {
    "bad_cases": "bad_cases.jsonl",
    "bad_case_updates": "bad_case_updates.jsonl",
}


class BadCaseArtifactError(ValueError):
    """Raised when a Bad Case artifact cannot be parsed or written."""


def load_bad_cases(result_dir: str | Path) -> list[dict[str, Any]]:
    return [
        BadCaseRecord.model_validate(row).model_dump()
        for row in _read_jsonl(_result_dir(result_dir) / BAD_CASE_ARTIFACTS["bad_cases"])
    ]


def append_bad_case(
    result_dir: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    sequence = len(load_bad_cases(run_dir)) + 1
    payload = dict(record)
    payload.setdefault("run_id", _run_id(run_dir, payload))
    payload.setdefault("video_id", _video_id(run_dir, payload))
    payload.setdefault("event_id", None)
    payload.setdefault("track_id", None)
    payload.setdefault("frame_index", None)
    payload.setdefault("description", "")
    payload.setdefault("expected_result", "")
    payload.setdefault("actual_result", "")
    payload.setdefault("root_cause", "")
    payload.setdefault("snapshot_path", None)
    payload.setdefault("tags", [])
    payload.setdefault("status", "open")
    payload.setdefault("source", "manual")
    payload.setdefault("linked_review_id", None)
    payload.setdefault("linked_failed_case_id", None)
    now = _utc_now_iso()
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", payload["created_at"])
    payload.setdefault("case_id", _stable_id("badcase", payload, sequence))
    normalized = BadCaseRecord.model_validate(payload).model_dump()
    _append_jsonl(run_dir / BAD_CASE_ARTIFACTS["bad_cases"], normalized)
    _refresh_bad_case_artifact_metadata(run_dir)
    return normalized


def get_bad_case(result_dir: str | Path, case_id: str) -> dict[str, Any]:
    for record in load_bad_cases(result_dir):
        if record["case_id"] == case_id:
            return record
    raise KeyError(case_id)


def update_bad_case(
    result_dir: str | Path,
    case_id: str,
    updates: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _result_dir(result_dir)
    records = load_bad_cases(run_dir)
    sanitized_updates = {
        str(key): value
        for key, value in dict(updates).items()
        if value is not None and key in _UPDATABLE_FIELDS
    }
    if not sanitized_updates:
        raise ValueError("no supported bad case fields to update")

    updated_records: list[dict[str, Any]] = []
    updated_record: dict[str, Any] | None = None
    for record in records:
        if record["case_id"] != case_id:
            updated_records.append(record)
            continue
        candidate = {
            **record,
            **sanitized_updates,
            "updated_at": _utc_now_iso(),
        }
        updated_record = BadCaseRecord.model_validate(candidate).model_dump()
        updated_records.append(updated_record)

    if updated_record is None:
        raise KeyError(case_id)

    _write_jsonl_atomic(run_dir / BAD_CASE_ARTIFACTS["bad_cases"], updated_records)
    audit = BadCaseUpdateAuditRecord(
        run_id=updated_record["run_id"],
        case_id=updated_record["case_id"],
        updated_fields=sorted(sanitized_updates),
        updated_at=updated_record["updated_at"],
    ).model_dump()
    _append_jsonl(run_dir / BAD_CASE_ARTIFACTS["bad_case_updates"], audit)
    _refresh_bad_case_artifact_metadata(run_dir)
    return updated_record


def filter_bad_cases(
    records: list[dict[str, Any]],
    *,
    case_type: str | None = None,
    module: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if (case_type is None or record.get("case_type") == case_type)
        and (module is None or record.get("module") == module)
        and (status is None or record.get("status") == status)
        and (source is None or record.get("source") == source)
        and (tag is None or tag in record.get("tags", []))
    ]


def summarize_bad_case_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    tag_counts: Counter[str] = Counter()
    for record in records:
        tag_counts.update(str(tag) for tag in record.get("tags", []))
    return BadCaseSummary(
        total=len(records),
        by_type=dict(Counter(str(record.get("case_type")) for record in records)),
        by_module=dict(Counter(str(record.get("module")) for record in records)),
        by_status=dict(Counter(str(record.get("status")) for record in records)),
        by_source=dict(Counter(str(record.get("source")) for record in records)),
        top_tags=dict(tag_counts.most_common(20)),
    ).model_dump()


def _refresh_bad_case_artifact_metadata(run_dir: Path) -> None:
    summaries = {
        key: _bad_case_artifact_summary(run_dir, key, relative_path)
        for key, relative_path in BAD_CASE_ARTIFACTS.items()
    }
    _refresh_metadata(run_dir, summaries)
    _refresh_manifest(run_dir, summaries)
    _refresh_artifact_index(run_dir, summaries)


def _refresh_metadata(run_dir: Path, summaries: Mapping[str, dict[str, Any]]) -> None:
    metadata_path = run_dir / "metadata.json"
    metadata = _read_json(metadata_path) if metadata_path.is_file() else {}
    metadata.setdefault("run_id", _run_id(run_dir, metadata))
    artifacts = dict(metadata.get("artifacts", {}))
    artifacts.update(BAD_CASE_ARTIFACTS)
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


def _bad_case_artifact_summary(
    run_dir: Path,
    key: str,
    relative_path: str,
) -> dict[str, Any]:
    path = run_dir / relative_path
    try:
        record_count = _record_count(path)
        if not path.is_file():
            status = "missing"
        elif record_count == 0:
            status = "empty"
        else:
            status = "available"
    except OSError:
        status = "error"
        record_count = 0
    return {
        "status": status,
        "path": relative_path,
        "format": "jsonl",
        "record_count": record_count,
        "required": False,
        "stage": "stage_8b_bad_case_artifacts",
    }


def _record_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


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
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise BadCaseArtifactError(
                    f"malformed bad case artifact {path.name} at line {line_number}"
                ) from exc
            if not isinstance(payload, dict):
                raise BadCaseArtifactError(
                    f"malformed bad case artifact {path.name} at line {line_number}"
                )
            rows.append(payload)
    return rows


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
        file.write("\n")


def _write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            file.write("\n")
    temporary_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise BadCaseArtifactError(f"invalid JSON in {path.name}") from exc
    if not isinstance(payload, dict):
        raise BadCaseArtifactError(f"expected JSON object in {path.name}")
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


def _video_id(run_dir: Path, payload: Mapping[str, Any]) -> str | None:
    value = payload.get("video_id")
    if value:
        return str(value)
    metadata_path = run_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = _read_json(metadata_path)
        metadata_video_id = metadata.get("video_id")
        if metadata_video_id:
            return str(metadata_video_id)
    return None


def _result_dir(result_dir: str | Path) -> Path:
    return Path(result_dir)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


_UPDATABLE_FIELDS = {
    "status",
    "root_cause",
    "tags",
    "description",
    "expected_result",
    "actual_result",
    "snapshot_path",
    "linked_failed_case_id",
}
