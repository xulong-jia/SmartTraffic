from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.regression_metrics import regression_failed_cases
from app.core.config import get_settings
from app.core.paths import PROJECT_DIR
from app.repositories import (
    EvaluationDatasetRepository,
    EvaluationResultRepository,
    TrafficAnalysisRunRepository,
)
from app.services.bad_case_service import BadCaseService


class EvaluationDatasetNotFound(KeyError):
    """Raised when an Evaluation dataset id is not registered."""


class EvaluationService:
    """Stage 8EFG artifact-backed Evaluation Center MVP."""

    def __init__(
        self,
        *,
        results_dir: str | Path | None = None,
        eval_root: str | Path | None = None,
        session: Session | None = None,
    ) -> None:
        self.results_dir = Path(results_dir or get_settings().results_dir)
        self.eval_root = Path(eval_root or os.environ.get("SMARTTRAFFIC_EVALS_DIR", PROJECT_DIR / "evals"))
        self.session = session

    def list_datasets(self) -> dict[str, Any]:
        datasets = self._list_db_datasets()
        if datasets:
            return {
                "schema_version": "stage8efg.v1",
                "datasets": _with_ad_hoc_run_datasets(
                    datasets,
                    self._list_db_evaluation_runs(
                        run_id=None,
                        dataset_id=None,
                        evaluation_type=None,
                    ),
                ),
            }
        payload = load_evaluation_datasets(self.eval_root)
        payload["datasets"] = _with_ad_hoc_run_datasets(
            payload["datasets"],
            load_evaluation_runs(self.eval_root),
        )
        return payload

    def register_dataset(self, record: Mapping[str, Any]) -> dict[str, Any]:
        artifact_record = register_evaluation_dataset(self.eval_root, record)
        if self.session is not None:
            try:
                repo = EvaluationDatasetRepository(self.session)
                existing = repo.get(str(artifact_record["dataset_id"]))
                values = {
                    "name": artifact_record["name"],
                    "dataset_type": artifact_record["dataset_type"],
                    "version": str(artifact_record.get("metadata", {}).get("version") or ""),
                    "status": "active",
                    "config": artifact_record,
                }
                if existing is None:
                    repo.create(id=artifact_record["dataset_id"], **values)
                else:
                    repo.update(artifact_record["dataset_id"], **values)
            except SQLAlchemyError:
                pass
        return artifact_record

    def list_evaluation_runs(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        evaluation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        db_runs = self._list_db_evaluation_runs(
            run_id=run_id,
            dataset_id=dataset_id,
            evaluation_type=evaluation_type,
        )
        if db_runs:
            return db_runs
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
        dataset_id: str | None = None,
        evaluation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        db_results = self._list_db_results(
            run_id=run_id,
            evaluation_run_id=evaluation_run_id,
            dataset_id=dataset_id,
            evaluation_type=evaluation_type,
        )
        if db_results:
            return db_results
        return [
            result
            for result in load_evaluation_results(self.eval_root)
            if (run_id is None or result.get("run_id") == run_id)
            and (evaluation_run_id is None or result.get("evaluation_run_id") == evaluation_run_id)
            and (dataset_id is None or result.get("dataset_id") == dataset_id)
            and (evaluation_type is None or result.get("evaluation_type") == evaluation_type)
        ]

    def list_failed_cases(
        self,
        *,
        run_id: str | None = None,
        evaluation_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        db_failed_cases = self._list_db_failed_cases(
            run_id=run_id,
            evaluation_run_id=evaluation_run_id,
        )
        if db_failed_cases:
            return db_failed_cases
        return [
            failed_case
            for failed_case in load_failed_cases(self.eval_root)
            if (run_id is None or failed_case.get("run_id") == run_id)
            and (evaluation_run_id is None or failed_case.get("evaluation_run_id") == evaluation_run_id)
        ]

    def get_evaluation_summary(self, run_id: str) -> dict[str, Any]:
        db_summary = self._db_evaluation_summary(run_id)
        if db_summary is not None:
            return db_summary
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
        dataset = self._dataset(dataset_id, evaluation_type=evaluation_type) if dataset_id else None
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
        summary = self._write_run_summary(
            run_dir,
            run_id,
            extra_results=results,
            extra_failed_cases=saved_failed_cases,
        )
        if self._db_run_exists(run_id):
            self._persist_db_evaluation(
                run_id=run_id,
                requested_dataset_id=dataset_id,
                evaluation_run=evaluation_run,
                results=results,
                summary=summary,
                failed_cases=saved_failed_cases,
            )
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
                expected_events=_load_expected_events(
                    self.eval_root,
                    dataset,
                    run_id=run_dir.name,
                ),
                actual_events=_read_jsonl(run_dir / "events.jsonl"),
                frame_tolerance=int(config.get("frame_tolerance", 5)),
            )
            return [
                ("event_accuracy", details["event_accuracy"], details),
                ("event_precision", details["precision"], details),
                ("event_recall", details["recall"], details),
                ("event_f1", details["f1"], details),
                ("false_alarm_rate", details["false_alarm_rate"], details),
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
            if details.get("status") != "available":
                return [("detection_status", None, details)], []
            overall = dict(details.get("overall") or {})
            rows: list[tuple[str, int | float | str | None, dict[str, Any]]] = [
                ("detection_mAP", overall.get("mAP"), details),
                ("detection_precision", overall.get("precision"), details),
                ("detection_recall", overall.get("recall"), details),
            ]
            per_class = details.get("per_class")
            if isinstance(per_class, dict):
                for class_name in sorted(per_class):
                    class_details = per_class[class_name]
                    if isinstance(class_details, dict):
                        rows.append((f"detection_ap_{class_name}", class_details.get("ap"), details))
            return rows, []
        if evaluation_type == "tracking":
            details = compute_tracking_metrics(
                _load_annotation_payload(self.eval_root, dataset),
                _read_jsonl(run_dir / "tracks.jsonl"),
            )
            if details.get("status") != "available":
                return [("tracking_status", None, details)], []
            return [
                ("tracking_idf1", details.get("idf1"), details),
                ("tracking_mota", details.get("mota"), details),
                ("tracking_id_switches", details.get("id_switch_count"), details),
                ("tracking_track_lost", details.get("track_lost_count"), details),
            ], _tracking_failed_cases(details)
        details = self._bad_case_regression_summary(
            run_id=run_dir.name,
            run_dir=run_dir,
            config=config,
        )
        return [
            (
                "bad_case_regression_pass_rate",
                details["regression_pass_rate"],
                details,
            ),
            ("bad_case_regression_total_cases", details["total_case_count"], details),
            ("bad_case_regression_failed_cases", details["failed_case_count"], details),
            ("bad_case_regression_fixed_cases", details["fixed_case_count"], details),
            ("bad_case_regression_reopened_cases", details["reopened_case_count"], details),
        ], regression_failed_cases(details)

    def _write_run_summary(
        self,
        run_dir: Path,
        run_id: str,
        *,
        extra_results: list[dict[str, Any]] | None = None,
        extra_failed_cases: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        results = [*self.list_results(run_id=run_id), *(extra_results or [])]
        failed_cases = [*self.list_failed_cases(run_id=run_id), *(extra_failed_cases or [])]
        grouped: dict[str, dict[str, Any]] = {}
        for result in results:
            _set_latest_metric(grouped, result)
        regression = grouped.get("regression")
        if isinstance(regression, dict) and isinstance(regression.get("bad_case_regression_pass_rate"), dict):
            grouped["bad_case_regression"] = regression["bad_case_regression_pass_rate"].get("details", {})
        else:
            grouped["bad_case_regression"] = self._bad_case_regression_summary(
                run_id=run_id,
                run_dir=run_dir,
                config={},
            )
        return write_evaluation_summary(
            run_dir,
            {
                "run_id": run_id,
                "summary": grouped,
                "failed_cases": failed_cases,
            },
        )

    def _bad_case_regression_summary(
        self,
        *,
        run_id: str,
        run_dir: Path,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        service = BadCaseService(
            artifact_writer=TrafficArtifactWriter(self.results_dir),
            eval_root=self.eval_root,
            session=self.session,
        )
        records = service.list_bad_cases(run_id=run_id)
        if not records and self.session is None:
            records = load_bad_cases(run_dir)
        details = compute_bad_case_regression_metrics(
            records,
            config={
                **config,
                "dataset_id": config.get("dataset_id"),
            },
        )
        if config.get("apply_updates"):
            updated_count = self._apply_regression_updates(
                service=service,
                run_id=run_id,
                details=details,
            )
            details["updated_case_count"] = updated_count
        return details

    def _apply_regression_updates(
        self,
        *,
        service: BadCaseService,
        run_id: str,
        details: dict[str, Any],
    ) -> int:
        updated_count = 0
        for result in details.get("case_results", []):
            if not isinstance(result, dict):
                continue
            case_id = str(result.get("bad_case_id") or "")
            suggested_status = result.get("suggested_status")
            if not case_id or suggested_status == result.get("previous_status"):
                continue
            if suggested_status not in {"fixed", "open"}:
                continue
            service.update_bad_case(
                run_id=run_id,
                case_id=case_id,
                updates={"status": suggested_status},
            )
            updated_count += 1
        return updated_count

    def _dataset(
        self,
        dataset_id: str | None,
        *,
        evaluation_type: str | None = None,
    ) -> dict[str, Any]:
        db_dataset = self._db_dataset(dataset_id)
        if db_dataset is not None:
            return _normalize_ad_hoc_dataset(db_dataset, evaluation_type=evaluation_type)
        for dataset in self.list_datasets()["datasets"]:
            if dataset["dataset_id"] == dataset_id:
                return _normalize_ad_hoc_dataset(dataset, evaluation_type=evaluation_type)
        if _is_ad_hoc_dataset_id(dataset_id, evaluation_type=evaluation_type):
            return _ad_hoc_dataset_record(dataset_id or f"adhoc-{evaluation_type}", evaluation_type or "event")
        raise EvaluationDatasetNotFound(dataset_id or "")

    def _existing_run_dir(self, run_id: str) -> Path:
        if self.session is not None:
            try:
                run = TrafficAnalysisRunRepository(self.session).get(run_id)
            except SQLAlchemyError:
                run = None
            if run is not None and run.result_dir:
                run_dir = Path(run.result_dir)
                if run_dir.is_dir():
                    return run_dir
        run_dir = self.results_dir / run_id
        if not run_dir.is_dir():
            raise KeyError(run_id)
        return run_dir

    def _db_run_exists(self, run_id: str) -> bool:
        if self.session is None:
            return False
        try:
            return TrafficAnalysisRunRepository(self.session).get(run_id) is not None
        except SQLAlchemyError:
            return False

    def _list_db_datasets(self) -> list[dict[str, Any]]:
        if self.session is None:
            return []
        try:
            return [
                _dataset_from_model(row)
                for row in EvaluationDatasetRepository(self.session).list()
            ]
        except SQLAlchemyError:
            return []

    def _db_dataset(self, dataset_id: str | None) -> dict[str, Any] | None:
        if self.session is None or dataset_id is None:
            return None
        try:
            row = EvaluationDatasetRepository(self.session).get(dataset_id)
        except SQLAlchemyError:
            return None
        return _dataset_from_model(row) if row is not None else None

    def _ensure_db_dataset(
        self,
        dataset_id: str | None,
        evaluation_type: str,
    ) -> str:
        assert self.session is not None
        if dataset_id is not None:
            if EvaluationDatasetRepository(self.session).get(dataset_id) is not None:
                return dataset_id
            dataset = self._dataset(dataset_id, evaluation_type=evaluation_type)
            EvaluationDatasetRepository(self.session).create(
                id=dataset["dataset_id"],
                name=dataset["name"],
                dataset_type=str(dataset["dataset_type"]),
                version=str(dataset.get("metadata", {}).get("version") or ""),
                status="active",
                config=dataset,
            )
            return dataset_id
        default_id = f"adhoc-{evaluation_type}"[:64]
        repo = EvaluationDatasetRepository(self.session)
        if repo.get(default_id) is None:
            now = _utc_now_iso()
            repo.create(
                id=default_id,
                name=f"Ad hoc {evaluation_type}",
                dataset_type=evaluation_type,
                version="stage3ef",
                status="active",
                config={
                    "dataset_id": default_id,
                    "name": f"Ad hoc {evaluation_type}",
                    "dataset_type": evaluation_type,
                    "source": "ad_hoc",
                    "metadata": {},
                    "created_at": now,
                },
            )
        return default_id

    def _persist_db_evaluation(
        self,
        *,
        run_id: str,
        requested_dataset_id: str | None,
        evaluation_run: dict[str, Any],
        results: list[dict[str, Any]],
        summary: dict[str, Any],
        failed_cases: list[dict[str, Any]],
    ) -> None:
        if self.session is None:
            return
        dataset_id = self._ensure_db_dataset(
            requested_dataset_id,
            str(evaluation_run["evaluation_type"]),
        )
        repo = EvaluationResultRepository(self.session)
        for result in results:
            row_summary = {
                "evaluation_run": evaluation_run,
                "requested_dataset_id": requested_dataset_id,
                "summary": summary.get("summary", {}),
                "failed_cases": failed_cases,
            }
            if repo.get(result["evaluation_result_id"]) is None:
                repo.create(
                    id=result["evaluation_result_id"],
                    dataset_id=dataset_id,
                    run_id=run_id,
                    evaluation_type=str(result["evaluation_type"]),
                    status=str(evaluation_run["status"]),
                    metrics={
                        "metric_name": result["metric_name"],
                        "metric_value": result.get("metric_value"),
                        "details": result.get("details", {}),
                    },
                    summary=row_summary,
                )

    def _list_db_results(
        self,
        *,
        run_id: str | None,
        evaluation_run_id: str | None,
        dataset_id: str | None,
        evaluation_type: str | None,
    ) -> list[dict[str, Any]]:
        if self.session is None:
            return []
        try:
            rows = EvaluationResultRepository(self.session).list(
                run_id=run_id,
                evaluation_type=evaluation_type,
            )
        except SQLAlchemyError:
            return []
        records = [_result_from_model(row) for row in rows]
        if evaluation_run_id is not None:
            records = [
                record
                for record in records
                if record.get("evaluation_run_id") == evaluation_run_id
            ]
        if dataset_id is not None:
            records = [
                record
                for record in records
                if record.get("dataset_id") == dataset_id
            ]
        return records

    def _list_db_evaluation_runs(
        self,
        *,
        run_id: str | None,
        dataset_id: str | None,
        evaluation_type: str | None,
    ) -> list[dict[str, Any]]:
        runs_by_id: dict[str, dict[str, Any]] = {}
        for result in self._list_db_results(
            run_id=run_id,
            evaluation_run_id=None,
            dataset_id=None,
            evaluation_type=evaluation_type,
        ):
            evaluation_run_id = result["evaluation_run_id"]
            run_record = dict(result.get("_evaluation_run") or {})
            if not run_record:
                run_record = {
                    "evaluation_run_id": evaluation_run_id,
                    "dataset_id": result.get("dataset_id"),
                    "run_id": result["run_id"],
                    "evaluation_type": result["evaluation_type"],
                    "status": "completed",
                    "started_at": result["created_at"],
                    "finished_at": result["created_at"],
                    "config": {},
                }
            if dataset_id is not None and run_record.get("dataset_id") != dataset_id:
                continue
            runs_by_id[evaluation_run_id] = run_record
        return list(runs_by_id.values())

    def _list_db_failed_cases(
        self,
        *,
        run_id: str | None,
        evaluation_run_id: str | None,
    ) -> list[dict[str, Any]]:
        failed_by_id: dict[str, dict[str, Any]] = {}
        for row in self._db_result_rows(run_id=run_id):
            for failed_case in _failed_cases_from_model(row):
                if evaluation_run_id is not None and failed_case.get("evaluation_run_id") != evaluation_run_id:
                    continue
                failed_by_id[str(failed_case["failed_case_id"])] = failed_case
        return list(failed_by_id.values())

    def _db_evaluation_summary(self, run_id: str) -> dict[str, Any] | None:
        rows = self._db_result_rows(run_id=run_id)
        if not rows:
            if self._db_run_exists(run_id):
                return {
                    "schema_version": "stage8efg.v1",
                    "run_id": run_id,
                    "generated_at": None,
                    "summary": {},
                    "failed_cases": [],
                }
            return None
        grouped: dict[str, dict[str, Any]] = {}
        failed_cases: dict[str, dict[str, Any]] = {}
        generated_at = None
        for row in rows:
            record = _result_from_model(row)
            _set_latest_metric(
                grouped,
                {key: value for key, value in record.items() if not key.startswith("_")},
            )
            if generated_at is None or str(record["created_at"]) > generated_at:
                generated_at = record["created_at"]
            for failed_case in _failed_cases_from_model(row):
                failed_cases[str(failed_case["failed_case_id"])] = failed_case
        if (
            isinstance(grouped.get("regression"), dict)
            and isinstance(grouped["regression"].get("bad_case_regression_pass_rate"), dict)
        ):
            grouped["bad_case_regression"] = grouped["regression"]["bad_case_regression_pass_rate"].get("details", {})
        return {
            "schema_version": "stage8efg.v1",
            "run_id": run_id,
            "generated_at": generated_at,
            "summary": grouped,
            "failed_cases": list(failed_cases.values()),
        }

    def _db_result_rows(self, *, run_id: str | None) -> list[Any]:
        if self.session is None:
            return []
        try:
            return EvaluationResultRepository(self.session).list(run_id=run_id)
        except SQLAlchemyError:
            return []


def _load_expected_events(
    eval_root: Path,
    dataset: dict[str, Any] | None,
    *,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    payload = _load_dataset_json(eval_root, dataset, "expected_events_path")
    dataset_events = _event_records(payload)
    if dataset_events:
        return dataset_events
    if run_id:
        run_payload = _read_json(eval_root / "expected" / f"{run_id}_expected_events.json")
        return _event_records(run_payload)
    return []


def _event_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def _set_latest_metric(
    grouped: dict[str, dict[str, Any]],
    record: dict[str, Any],
) -> None:
    evaluation_type = str(record["evaluation_type"])
    metric_name = str(record["metric_name"])
    group = grouped.setdefault(evaluation_type, {})
    existing = group.get(metric_name)
    if existing is None or _result_order_key(record) >= _result_order_key(existing):
        group[metric_name] = record


def _result_order_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("created_at") or ""),
        str(record.get("evaluation_run_id") or ""),
        str(record.get("evaluation_result_id") or ""),
    )


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


def _normalize_ad_hoc_dataset(
    dataset: dict[str, Any],
    *,
    evaluation_type: str | None = None,
) -> dict[str, Any]:
    if not _is_ad_hoc_dataset_id(dataset.get("dataset_id"), evaluation_type=evaluation_type):
        return dataset
    return {
        **dataset,
        "source": "ad_hoc",
        "metadata": dataset.get("metadata") or {},
    }


def _is_ad_hoc_dataset(dataset: dict[str, Any] | None) -> bool:
    if not dataset:
        return False
    return dataset.get("source") == "ad_hoc" or _is_ad_hoc_dataset_id(dataset.get("dataset_id"))


def _is_ad_hoc_dataset_id(
    dataset_id: Any,
    *,
    evaluation_type: str | None = None,
) -> bool:
    if dataset_id is None:
        return False
    normalized = str(dataset_id)
    if normalized.startswith("adhoc-"):
        return True
    if evaluation_type and normalized == f"adhoc-{evaluation_type}"[:64]:
        return True
    return False


def _ad_hoc_dataset_record(dataset_id: str, evaluation_type: str) -> dict[str, Any]:
    now = _utc_now_iso()
    return {
        "dataset_id": dataset_id,
        "name": f"Ad hoc {evaluation_type}",
        "dataset_type": evaluation_type,
        "source": "ad_hoc",
        "annotation_path": None,
        "expected_events_path": None,
        "expected_counts_path": None,
        "metadata": {},
        "created_at": now,
    }


def _with_ad_hoc_run_datasets(
    datasets: list[dict[str, Any]],
    evaluation_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = {str(dataset["dataset_id"]): dataset for dataset in datasets}
    for run in evaluation_runs:
        dataset_id = run.get("dataset_id")
        evaluation_type = str(run.get("evaluation_type") or "event")
        if not _is_ad_hoc_dataset_id(dataset_id, evaluation_type=evaluation_type):
            continue
        normalized_id = str(dataset_id)
        merged.setdefault(
            normalized_id,
            _ad_hoc_dataset_record(normalized_id, evaluation_type),
        )
    return sorted(merged.values(), key=lambda item: str(item.get("dataset_id") or ""))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {}


def _tracking_failed_cases(details: dict[str, Any]) -> list[dict[str, Any]]:
    failed_cases: list[dict[str, Any]] = []
    for item in details.get("switch_details") or []:
        if not isinstance(item, dict):
            continue
        frame_index = _optional_int(item.get("frame_index"))
        failed_cases.append(
            {
                "failure_type": "id_switch",
                "module": "tracker",
                "expected": {
                    "gt_track_id": item.get("gt_track_id"),
                    "previous_track_id": item.get("previous_track_id"),
                },
                "actual": {
                    "new_track_id": item.get("new_track_id"),
                    "tags": ["tracker", "id_switch"],
                },
                "frame_range": {
                    "start_frame": frame_index,
                    "end_frame": frame_index,
                },
                "suggested_bad_case_type": "id_switch",
            }
        )
    for item in details.get("lost_track_details") or []:
        if not isinstance(item, dict):
            continue
        start_frame = _optional_int(item.get("start_frame"))
        end_frame = _optional_int(item.get("end_frame"))
        failed_cases.append(
            {
                "failure_type": "track_lost",
                "module": "tracker",
                "expected": {
                    "gt_track_id": item.get("gt_track_id"),
                    "frame_range": {
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                    },
                },
                "actual": {
                    "track_id": None,
                    "tags": ["tracker", "track_lost"],
                },
                "frame_range": {
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                },
                "suggested_bad_case_type": "track_lost",
            }
        )
    return failed_cases


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _dataset_from_model(row: Any) -> dict[str, Any]:
    config = dict(row.config or {})
    return {
        "dataset_id": row.id,
        "name": row.name,
        "dataset_type": row.dataset_type,
        "source": config.get("source") or "custom_annotation",
        "annotation_path": config.get("annotation_path"),
        "expected_events_path": config.get("expected_events_path"),
        "expected_counts_path": config.get("expected_counts_path"),
        "metadata": config.get("metadata") or {},
        "created_at": config.get("created_at") or _datetime_iso(row.created_at),
    }


def _result_from_model(row: Any) -> dict[str, Any]:
    metrics = dict(row.metrics or {})
    summary = dict(row.summary or {})
    evaluation_run = dict(summary.get("evaluation_run") or {})
    evaluation_run_id = str(
        evaluation_run.get("evaluation_run_id")
        or summary.get("evaluation_run_id")
        or row.id
    )
    requested_dataset_id = summary.get("requested_dataset_id")
    return {
        "evaluation_result_id": row.id,
        "evaluation_run_id": evaluation_run_id,
        "run_id": row.run_id,
        "dataset_id": requested_dataset_id if requested_dataset_id is not None else row.dataset_id,
        "evaluation_type": row.evaluation_type,
        "metric_name": str(metrics.get("metric_name") or "summary"),
        "metric_value": metrics.get("metric_value"),
        "details": dict(metrics.get("details") or {}),
        "created_at": _datetime_iso(row.created_at),
        "_evaluation_run": evaluation_run,
    }


def _failed_cases_from_model(row: Any) -> list[dict[str, Any]]:
    summary = dict(row.summary or {})
    failed_cases = summary.get("failed_cases")
    if isinstance(failed_cases, list):
        return [item for item in failed_cases if isinstance(item, dict)]
    metrics = dict(row.metrics or {})
    details = metrics.get("details")
    if isinstance(details, dict) and isinstance(details.get("failed_cases"), list):
        return [item for item in details["failed_cases"] if isinstance(item, dict)]
    return []


def _datetime_iso(value: datetime | None) -> str:
    if value is None:
        return _utc_now_iso()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).replace(microsecond=0).isoformat()
    return value.astimezone(UTC).replace(microsecond=0).isoformat()
