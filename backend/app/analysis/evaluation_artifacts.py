from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from app.schemas.evaluation import (
    EvaluationDatasetRecord,
    EvaluationDatasetRegistry,
    EvaluationResultRecord,
    EvaluationRunRecord,
    EvaluationSummaryArtifact,
    FailedCaseRecord,
)


STAGE8EFG_SCHEMA_VERSION = "stage8efg.v1"
EVALUATION_DATASETS_PATH = "datasets/evaluation_datasets.json"
EVALUATION_RUNS_PATH = "results/evaluation_runs.jsonl"
EVALUATION_RESULTS_PATH = "results/evaluation_results.jsonl"
FAILED_CASES_PATH = "results/failed_cases.jsonl"


class EvaluationArtifactError(ValueError):
    """Raised when an Evaluation artifact cannot be parsed or written."""


def load_evaluation_datasets(eval_root: str | Path) -> dict[str, Any]:
    path = _eval_root(eval_root) / EVALUATION_DATASETS_PATH
    if not path.is_file():
        return EvaluationDatasetRegistry(
            schema_version=STAGE8EFG_SCHEMA_VERSION,
            datasets=[],
        ).model_dump()
    payload = _read_json(path)
    payload.setdefault("schema_version", STAGE8EFG_SCHEMA_VERSION)
    payload.setdefault("datasets", [])
    return EvaluationDatasetRegistry.model_validate(payload).model_dump()


def register_evaluation_dataset(
    eval_root: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    root = _eval_root(eval_root)
    registry = load_evaluation_datasets(root)
    payload = dict(record)
    payload.setdefault("source", "custom_annotation")
    payload.setdefault("metadata", {})
    payload.setdefault("created_at", _utc_now_iso())
    normalized = EvaluationDatasetRecord.model_validate(payload).model_dump()
    datasets = [
        dataset
        for dataset in registry["datasets"]
        if dataset["dataset_id"] != normalized["dataset_id"]
    ]
    datasets.append(normalized)
    datasets.sort(key=lambda item: item["dataset_id"])
    _write_json_atomic(
        {
            "schema_version": STAGE8EFG_SCHEMA_VERSION,
            "datasets": datasets,
        },
        root / EVALUATION_DATASETS_PATH,
    )
    return normalized


def load_evaluation_runs(eval_root: str | Path) -> list[dict[str, Any]]:
    return [
        EvaluationRunRecord.model_validate(row).model_dump()
        for row in _read_jsonl(_eval_root(eval_root) / EVALUATION_RUNS_PATH)
    ]


def append_evaluation_run(
    eval_root: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(record)
    payload.setdefault("evaluation_run_id", _stable_id("evalrun", payload, _next_sequence(eval_root, EVALUATION_RUNS_PATH)))
    normalized = EvaluationRunRecord.model_validate(payload).model_dump()
    _append_jsonl(_eval_root(eval_root) / EVALUATION_RUNS_PATH, normalized)
    return normalized


def load_evaluation_results(eval_root: str | Path) -> list[dict[str, Any]]:
    return [
        EvaluationResultRecord.model_validate(row).model_dump()
        for row in _read_jsonl(_eval_root(eval_root) / EVALUATION_RESULTS_PATH)
    ]


def append_evaluation_result(
    eval_root: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(record)
    payload.setdefault(
        "evaluation_result_id",
        _stable_id("evalresult", payload, _next_sequence(eval_root, EVALUATION_RESULTS_PATH)),
    )
    normalized = EvaluationResultRecord.model_validate(payload).model_dump()
    _append_jsonl(_eval_root(eval_root) / EVALUATION_RESULTS_PATH, normalized)
    return normalized


def load_failed_cases(eval_root: str | Path) -> list[dict[str, Any]]:
    return [
        FailedCaseRecord.model_validate(row).model_dump()
        for row in _read_jsonl(_eval_root(eval_root) / FAILED_CASES_PATH)
    ]


def append_failed_case(
    eval_root: str | Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(record)
    payload.setdefault(
        "failed_case_id",
        _stable_id("failedcase", payload, _next_sequence(eval_root, FAILED_CASES_PATH)),
    )
    normalized = FailedCaseRecord.model_validate(payload).model_dump()
    _append_jsonl(_eval_root(eval_root) / FAILED_CASES_PATH, normalized)
    return normalized


def load_evaluation_summary(run_dir: str | Path) -> dict[str, Any]:
    path = Path(run_dir) / "evaluation_summary.json"
    if not path.is_file():
        return EvaluationSummaryArtifact(
            schema_version=STAGE8EFG_SCHEMA_VERSION,
            run_id=Path(run_dir).name,
            generated_at=None,
            summary={},
            failed_cases=[],
        ).model_dump()
    payload = _read_json(path)
    payload.setdefault("schema_version", STAGE8EFG_SCHEMA_VERSION)
    payload.setdefault("run_id", Path(run_dir).name)
    payload.setdefault("generated_at", None)
    payload.setdefault("summary", {})
    payload.setdefault("failed_cases", [])
    return EvaluationSummaryArtifact.model_validate(payload).model_dump()


def write_evaluation_summary(
    run_dir: str | Path,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir_path = Path(run_dir)
    normalized = EvaluationSummaryArtifact.model_validate(
        {
            "schema_version": STAGE8EFG_SCHEMA_VERSION,
            "generated_at": _utc_now_iso(),
            **dict(payload),
        }
    ).model_dump()
    _write_json_atomic(normalized, run_dir_path / "evaluation_summary.json")
    _refresh_evaluation_artifact_metadata(run_dir_path)
    return normalized


def _refresh_evaluation_artifact_metadata(run_dir: Path) -> None:
    summary = _evaluation_artifact_summary(run_dir)
    _refresh_metadata(run_dir, summary)
    _refresh_manifest(run_dir, summary)
    _refresh_artifact_index(run_dir, summary)


def _evaluation_artifact_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "evaluation_summary.json"
    status = "missing"
    if path.is_file():
        payload = _read_json(path)
        status = "available" if payload.get("summary") else "empty"
    return {
        "status": status,
        "path": "evaluation_summary.json",
        "format": "json",
        "record_count": 1 if path.is_file() else 0,
        "required": False,
        "stage": "stage_8efg_evaluation_center_mvp",
    }


def _refresh_metadata(run_dir: Path, summary: Mapping[str, Any]) -> None:
    metadata_path = run_dir / "metadata.json"
    metadata = _read_json(metadata_path) if metadata_path.is_file() else {}
    metadata.setdefault("run_id", run_dir.name)
    artifacts = dict(metadata.get("artifacts", {}))
    artifacts["evaluation_summary"] = "evaluation_summary.json"
    metadata["artifacts"] = artifacts
    artifact_summary = dict(metadata.get("artifact_summary", {}))
    artifact_summary["evaluation_summary"] = {
        "status": summary["status"],
        "path": summary["path"],
        "record_count": summary["record_count"],
    }
    metadata["artifact_summary"] = artifact_summary
    metadata["updated_at"] = _utc_now_iso()
    _write_json_atomic(metadata, metadata_path)


def _refresh_manifest(run_dir: Path, summary: Mapping[str, Any]) -> None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = _read_json(manifest_path)
    artifacts = dict(manifest.get("artifacts", {}))
    artifacts["evaluation_summary"] = dict(summary)
    manifest["artifacts"] = artifacts
    manifest["updated_at"] = _utc_now_iso()
    _write_json_atomic(manifest, manifest_path)


def _refresh_artifact_index(run_dir: Path, summary: Mapping[str, Any]) -> None:
    artifact_index_path = run_dir / "artifact_index.json"
    if not artifact_index_path.is_file():
        return
    artifact_index = _read_json(artifact_index_path)
    artifacts = dict(artifact_index.get("artifacts", {}))
    if summary["status"] in {"available", "empty"}:
        artifacts["evaluation_summary"] = "evaluation_summary.json"
    else:
        artifacts.pop("evaluation_summary", None)
    artifact_index["artifacts"] = artifacts
    _write_json_atomic(artifact_index, artifact_index_path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise EvaluationArtifactError(f"invalid JSON in {path.name}") from exc
    if not isinstance(payload, dict):
        raise EvaluationArtifactError(f"expected JSON object in {path.name}")
    return payload


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
                raise EvaluationArtifactError(
                    f"malformed evaluation artifact {path.name} at line {line_number}"
                ) from exc
            if not isinstance(payload, dict):
                raise EvaluationArtifactError(
                    f"malformed evaluation artifact {path.name} at line {line_number}"
                )
            rows.append(payload)
    return rows


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
        file.write("\n")


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


def _next_sequence(eval_root: str | Path, relative_path: str) -> int:
    return len(_read_jsonl(_eval_root(eval_root) / relative_path)) + 1


def _eval_root(eval_root: str | Path) -> Path:
    return Path(eval_root)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
