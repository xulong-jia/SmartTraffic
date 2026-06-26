from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from app.analysis.evaluation_artifacts import (
    append_failed_case,
    append_evaluation_result,
    append_evaluation_run,
    load_evaluation_datasets,
    load_evaluation_results,
    load_evaluation_runs,
    load_failed_cases,
    load_evaluation_summary,
    register_evaluation_dataset,
    write_evaluation_summary,
)
from app.analysis.evaluation_metrics import (
    compute_bad_case_regression_metrics,
    compute_detection_metrics,
    compute_event_metrics,
    compute_flow_counting_metrics,
    compute_tracking_metrics,
    compute_trajectory_metrics,
)
from app.analysis.bad_case_artifacts import load_bad_cases
from app.core.config import get_settings
from app.core.paths import PROJECT_DIR


class EvaluationDatasetNotFound(KeyError):
    """Raised when an Evaluation dataset id is not registered."""


class EvaluationService:
    """Stage 8EFG artifact-backed Evaluation Center MVP."""

    def __init__(
        self,
        *,
        results_dir: str | Path | None = None,
        eval_root: str | Path | None = None,
    ) -> None:
        self.results_dir = Path(results_dir or get_settings().results_dir)
        self.eval_root = Path(eval_root or os.environ.get("SMARTTRAFFIC_EVALS_DIR", PROJECT_DIR / "evals"))

    def list_datasets(self) -> dict[str, Any]:
        return load_evaluation_datasets(self.eval_root)

    def register_dataset(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return register_evaluation_dataset(self.eval_root, record)

    def list_evaluation_runs(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        evaluation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            run
            for run in load_evaluation_runs(self.eval_root)
            if (run_id is None or run.get("run_id") == run_id)
            and (dataset_id is None or run.get("dataset_id") == dataset_id)
            and (evaluation_type is None or run.get("evaluation_type") == evaluation_type)
        ]

    def list_results(
        self,
        *,
        run_id: str | None = None,
        evaluation_run_id: str | None = None,
        evaluation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            result
            for result in load_evaluation_results(self.eval_root)
            if (run_id is None or result.get("run_id") == run_id)
            and (evaluation_run_id is None or result.get("evaluation_run_id") == evaluation_run_id)
            and (evaluation_type is None or result.get("evaluation_type") == evaluation_type)
        ]

    def list_failed_cases(
        self,
        *,
        run_id: str | None = None,
        evaluation_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            failed_case
            for failed_case in load_failed_cases(self.eval_root)
            if (run_id is None or failed_case.get("run_id") == run_id)
            and (evaluation_run_id is None or failed_case.get("evaluation_run_id") == evaluation_run_id)
        ]

    def get_evaluation_summary(self, run_id: str) -> dict[str, Any]:
        return load_evaluation_summary(self._existing_run_dir(run_id))

    def run_evaluation(
        self,
        *,
        run_id: str,
        dataset_id: str | None = None,
        evaluation_type: str = "event",
        config: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        dataset = self._dataset(dataset_id) if dataset_id else None
        started_at = _utc_now_iso()
        evaluation_run = append_evaluation_run(
            self.eval_root,
            {
                "run_id": run_id,
                "dataset_id": dataset_id,
                "evaluation_type": evaluation_type,
                "status": "completed",
                "started_at": started_at,
                "finished_at": started_at,
                "config": dict(config or {}),
            },
        )
        metrics, failed_cases = self._compute_metrics(
            run_dir=run_dir,
            dataset=dataset,
            evaluation_type=evaluation_type,
            config=dict(config or {}),
        )
        created_at = _utc_now_iso()
        results = [
            append_evaluation_result(
                self.eval_root,
                {
                    "evaluation_run_id": evaluation_run["evaluation_run_id"],
                    "run_id": run_id,
                    "dataset_id": dataset_id,
                    "evaluation_type": evaluation_type,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "details": details,
                    "created_at": created_at,
                },
            )
            for metric_name, metric_value, details in metrics
        ]
        saved_failed_cases = [
            append_failed_case(
                self.eval_root,
                {
                    **failed_case,
                    "evaluation_run_id": evaluation_run["evaluation_run_id"],
                    "run_id": run_id,
                    "dataset_id": dataset_id,
                    "created_at": created_at,
                },
            )
            for failed_case in failed_cases
        ]
        summary = self._write_run_summary(run_dir, run_id)
        return {
            "evaluation_run": evaluation_run,
            "results": results,
            "summary": summary,
            "failed_cases": saved_failed_cases,
        }

    def _compute_metrics(
        self,
        *,
        run_dir: Path,
        dataset: dict[str, Any] | None,
        evaluation_type: str,
        config: dict[str, Any],
    ) -> tuple[list[tuple[str, int | float | str | None, dict[str, Any]]], list[dict[str, Any]]]:
        if evaluation_type == "event":
            details = compute_event_metrics(
                expected_events=_load_expected_events(self.eval_root, dataset),
                actual_events=_read_jsonl(run_dir / "events.jsonl"),
                frame_tolerance=int(config.get("frame_tolerance", 5)),
            )
            return [
                ("event_precision", details["precision"], details),
                ("event_recall", details["recall"], details),
                ("event_f1", details["f1"], details),
            ], list(details.get("failed_cases", []))
        if evaluation_type == "flow_counting":
            details = compute_flow_counting_metrics(
                _load_expected_counts(self.eval_root, dataset),
                _read_json(run_dir / "flow_counts.json") if (run_dir / "flow_counts.json").is_file() else {},
            )
            return [
                ("flow_absolute_error", details["absolute_error"], details),
                ("flow_mae", details["mae"], details),
                ("flow_mape", details["mape"], details),
            ], []
        if evaluation_type == "trajectory":
            details = compute_trajectory_metrics(
                {"frames": _read_jsonl(run_dir / "trajectory_points.jsonl")}
            )
            return [
                ("trajectory_track_count", details["track_count"], details),
                (
                    "trajectory_total_points",
                    details["total_trajectory_points"],
                    details,
                ),
                (
                    "trajectory_average_speed",
                    details["average_speed"],
                    details,
                ),
            ], []
        if evaluation_type == "detection":
            details = compute_detection_metrics(
                _load_annotation_payload(self.eval_root, dataset),
                _read_jsonl(run_dir / "detections.jsonl"),
            )
            return [("detection_status", None, details)], []
        if evaluation_type == "tracking":
            details = compute_tracking_metrics(
                _load_annotation_payload(self.eval_root, dataset),
                _read_jsonl(run_dir / "tracks.jsonl"),
            )
            return [("tracking_status", None, details)], []
        details = self._bad_case_regression_summary(run_dir)
        return [
            (
                "bad_case_regression_pass_rate",
                details["regression_pass_rate"],
                details,
            ),
            ("bad_case_regression_total_cases", details["total_cases"], details),
        ], []

    def _write_run_summary(self, run_dir: Path, run_id: str) -> dict[str, Any]:
        results = self.list_results(run_id=run_id)
        failed_cases = self.list_failed_cases(run_id=run_id)
        grouped: dict[str, dict[str, Any]] = {}
        for result in results:
            grouped.setdefault(str(result["evaluation_type"]), {})[
                str(result["metric_name"])
            ] = result
        grouped["bad_case_regression"] = self._bad_case_regression_summary(run_dir)
        return write_evaluation_summary(
            run_dir,
            {
                "run_id": run_id,
                "summary": grouped,
                "failed_cases": failed_cases,
            },
        )

    def _bad_case_regression_summary(self, run_dir: Path) -> dict[str, Any]:
        return compute_bad_case_regression_metrics(load_bad_cases(run_dir))

    def _dataset(self, dataset_id: str | None) -> dict[str, Any]:
        for dataset in self.list_datasets()["datasets"]:
            if dataset["dataset_id"] == dataset_id:
                return dataset
        raise EvaluationDatasetNotFound(dataset_id or "")

    def _existing_run_dir(self, run_id: str) -> Path:
        run_dir = self.results_dir / run_id
        if not run_dir.is_dir():
            raise KeyError(run_id)
        return run_dir


def _load_expected_events(
    eval_root: Path,
    dataset: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    payload = _load_dataset_json(eval_root, dataset, "expected_events_path")
    if isinstance(payload.get("events"), list):
        return [event for event in payload["events"] if isinstance(event, dict)]
    return []


def _load_expected_counts(
    eval_root: Path,
    dataset: dict[str, Any] | None,
) -> dict[str, Any]:
    return _load_dataset_json(eval_root, dataset, "expected_counts_path")


def _load_annotation_payload(
    eval_root: Path,
    dataset: dict[str, Any] | None,
) -> dict[str, Any] | None:
    payload = _load_dataset_json(eval_root, dataset, "annotation_path")
    return payload or None


def _load_dataset_json(
    eval_root: Path,
    dataset: dict[str, Any] | None,
    path_key: str,
) -> dict[str, Any]:
    if not dataset or not dataset.get(path_key):
        return {}
    path = _resolve_eval_path(eval_root, str(dataset[path_key]))
    if not path.is_file():
        return {}
    return _read_json(path)


def _resolve_eval_path(eval_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == "evals":
        return eval_root.joinpath(*parts[1:])
    return eval_root / path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                payload = json.loads(stripped)
                if isinstance(payload, dict):
                    rows.append(payload)
    return rows


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
