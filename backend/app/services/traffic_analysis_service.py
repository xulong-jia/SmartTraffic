from typing import Any
import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.models import TrafficAnalysisRun
from app.repositories import (
    DetectionRepository,
    FlowCountRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    ZoneStatisticRepository,
)


STAGE6D_SCHEMA_VERSION = "stage6d.v1"
IGNORED_RUN_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
}


class TrafficAnalysisService:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def register_run(
        self,
        run_id: str,
        video_id: str,
        result_dir: str,
        artifact_index: dict[str, Any],
        status: str = "completed",
    ) -> dict[str, Any]:
        run = {
            "id": run_id,
            "video_id": video_id,
            "status": status,
            "result_dir": result_dir,
            "artifact_index": artifact_index,
        }
        self._runs[run_id] = run
        return dict(run)

    def list_runs(
        self,
        *,
        status: str | None = None,
        video_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: Session | None = None,
    ) -> dict[str, Any]:
        summaries_by_run_id: dict[str, dict[str, Any]] = {}
        if db is not None:
            for run in TrafficAnalysisRunRepository(db).list():
                summaries_by_run_id[run.id] = _db_run_summary(run)

        for run_dir in self.discover_run_directories():
            summaries_by_run_id.setdefault(
                run_dir.name,
                self.build_run_summary(run_dir.name),
            )

        for run_id, registry_run in self._runs.items():
            summaries_by_run_id.setdefault(
                run_id,
                self.build_run_summary(run_id, registry_run=registry_run),
            )

        summaries = [
            summary
            for summary in summaries_by_run_id.values()
            if _summary_matches(summary, status=status, video_id=video_id)
        ]
        summaries.sort(
            key=lambda summary: (_summary_sort_value(summary), str(summary["run_id"])),
            reverse=True,
        )
        total = len(summaries)
        safe_offset = max(offset, 0)
        safe_limit = max(limit, 0)
        return {
            "items": summaries[safe_offset : safe_offset + safe_limit],
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def get_run(self, run_id: str, db: Session | None = None) -> dict[str, Any]:
        if db is not None:
            run = TrafficAnalysisRunRepository(db).get(run_id)
            if run is not None:
                return _db_run_summary(run)
        registry_run = self._runs.get(run_id)
        return self.build_run_summary(run_id, registry_run=registry_run)

    def discover_run_directories(self) -> list[Path]:
        results_dir = self._results_dir()
        if not results_dir.is_dir():
            return []
        return sorted(
            child
            for child in results_dir.iterdir()
            if child.is_dir()
            and not child.name.startswith(".")
            and child.name not in IGNORED_RUN_DIR_NAMES
        )

    def build_run_summary(
        self,
        run_id: str,
        *,
        registry_run: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists() and registry_run is None:
            raise KeyError(run_id)

        metadata, metadata_state = _load_json_state(run_dir / "metadata.json")
        manifest, manifest_state = _load_json_state(run_dir / "manifest.json")
        artifact_index, artifact_index_state = _load_json_state(
            run_dir / "artifact_index.json"
        )
        source = _summary_source(
            manifest_state=manifest_state,
            metadata_state=metadata_state,
            artifact_index_state=artifact_index_state,
            registry_run=registry_run,
        )

        video_id = _first_string(
            _mapping_value(manifest, "video_id"),
            _mapping_value(metadata, "video_id"),
            _mapping_value(artifact_index, "video_id"),
            _mapping_value(registry_run, "video_id"),
            default="",
        )
        run_status = _first_string(
            _mapping_value(manifest, "status"),
            _mapping_value(metadata, "status"),
            _mapping_value(registry_run, "status"),
            default="completed",
        )
        result_dir = _public_result_dir(
            run_id,
            _mapping_value(manifest, "result_dir")
            or _mapping_value(metadata, "result_dir")
            or _mapping_value(artifact_index, "result_dir")
            or _mapping_value(registry_run, "result_dir"),
        )
        artifact_summary = _artifact_summary(
            run_dir=run_dir,
            manifest=manifest,
            metadata=metadata,
            artifact_index=artifact_index,
            registry_run=registry_run,
        )
        artifact_paths = _artifact_paths(
            metadata=metadata,
            artifact_index=artifact_index,
            registry_run=registry_run,
        )

        return {
            "id": run_id,
            "run_id": run_id,
            "video_id": video_id,
            "status": run_status,
            "mode": _first_string(_mapping_value(metadata, "mode"), default="offline"),
            "result_dir": result_dir,
            "created_at": _first_string(
                _mapping_value(manifest, "created_at"),
                _mapping_value(metadata, "created_at"),
                default="",
            ),
            "updated_at": _first_string(
                _mapping_value(manifest, "updated_at"),
                _mapping_value(metadata, "updated_at"),
                default="",
            ),
            "started_at": _first_string(
                _mapping_value(metadata, "started_at"),
                default="",
            ),
            "finished_at": _first_string(
                _mapping_value(metadata, "finished_at"),
                default="",
            ),
            "source": source,
            "schema_version": STAGE6D_SCHEMA_VERSION,
            "metadata": metadata_state,
            "manifest": {
                **manifest_state,
                "schema_version": (
                    str(manifest.get("schema_version"))
                    if isinstance(manifest, dict) and manifest.get("schema_version")
                    else None
                ),
            },
            "artifact_index": artifact_index_state,
            "artifact_paths": artifact_paths,
            "artifact_summary": artifact_summary,
        }

    def read_run_detections(
        self,
        run_id: str,
        limit: int = 100,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            rows = DetectionRepository(db).list(run_id=run_id)
            if rows:
                limited = rows[:limit] if limit > 0 else []
                return {
                    "run_id": run_id,
                    "video_id": _first_row_video_id(rows),
                    "summary": _db_result_summary(db, run_id),
                    "frames": _group_result_rows(limited, "detections"),
                    "rows": [_model_dict(row) for row in limited],
                    "limit": limit,
                    "source": "db",
                }
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "detection_summary.json"
        jsonl_path = run_dir / "detections.jsonl"
        csv_path = run_dir / "detections.csv"
        summary: dict[str, Any] = {}
        if summary_path.is_file():
            with summary_path.open(encoding="utf-8") as file:
                summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if jsonl_path.is_file():
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if stripped:
                        frames.append(json.loads(stripped))
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
            "source": "artifact",
        }

    def read_run_tracks(
        self,
        run_id: str,
        limit: int = 100,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            rows = TrackRepository(db).list(run_id=run_id)
            if rows:
                limited = rows[:limit] if limit > 0 else []
                return {
                    "run_id": run_id,
                    "video_id": _first_row_video_id(rows),
                    "summary": _db_result_summary(db, run_id),
                    "frames": _group_result_rows(limited, "tracks"),
                    "rows": [_model_dict(row) for row in limited],
                    "limit": limit,
                    "source": "db",
                }
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "tracking_summary.json"
        jsonl_path = run_dir / "tracks.jsonl"
        csv_path = run_dir / "tracks.csv"
        summary: dict[str, Any] = {}
        if summary_path.is_file():
            with summary_path.open(encoding="utf-8") as file:
                summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if jsonl_path.is_file():
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if stripped:
                        frames.append(json.loads(stripped))
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
            "source": "artifact",
        }

    def read_run_trajectory_points(
        self,
        run_id: str,
        limit: int = 100,
        track_id: int | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            rows = TrajectoryPointRepository(db).list(run_id=run_id)
            if track_id is not None:
                rows = [
                    row
                    for row in rows
                    if _track_id_matches(row.track_id, track_id)
                ]
            if rows:
                limited = rows[:limit] if limit > 0 else []
                return {
                    "run_id": run_id,
                    "video_id": _first_row_video_id(rows),
                    "summary": _db_result_summary(db, run_id),
                    "frames": _group_result_rows(limited, "trajectory_points"),
                    "rows": [_model_dict(row) for row in limited],
                    "limit": limit,
                    "track_id": track_id,
                    "source": "db",
                }
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "trajectory_summary.json"
        jsonl_path = run_dir / "trajectory_points.jsonl"
        csv_path = run_dir / "trajectory_points.csv"
        if (
            not summary_path.is_file()
            or not jsonl_path.is_file()
            or not csv_path.is_file()
        ):
            raise KeyError(run_id)

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if limit > 0:
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    frame = json.loads(stripped)
                    if track_id is not None:
                        frame = dict(frame)
                        frame["trajectory_points"] = [
                            point
                            for point in frame.get("trajectory_points", [])
                            if _track_id_matches(point.get("track_id"), track_id)
                        ]
                    frames.append(frame)
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if limit > 0:
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    if track_id is not None and not _track_id_matches(
                        row.get("track_id"),
                        track_id,
                    ):
                        continue
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
            "track_id": track_id,
            "source": "artifact",
        }

    def read_run_events(
        self,
        run_id: str,
        limit: int = 100,
        event_type: str | None = None,
        track_id: int | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "event_summary.json"
        events_path = run_dir / "events.jsonl"
        evidence_path = run_dir / "event_evidence.jsonl"
        executions_path = run_dir / "rule_executions.jsonl"
        if (
            not summary_path.is_file()
            or not events_path.is_file()
            or not evidence_path.is_file()
            or not executions_path.is_file()
        ):
            raise FileNotFoundError("event artifacts not found")

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        events: list[dict[str, Any]] = []
        event_ids: set[str] | None = None
        if limit > 0:
            for event in _read_jsonl_limited(
                events_path,
                limit=limit,
                predicate=lambda item: _event_matches(
                    item,
                    event_type=event_type,
                    track_id=track_id,
                ),
            ):
                events.append(event)
            if event_type is not None or track_id is not None:
                event_ids = {
                    str(event["event_id"])
                    for event in events
                    if event.get("event_id") is not None
                }

        event_evidence: list[dict[str, Any]] = []
        rule_executions: list[dict[str, Any]] = []
        if limit > 0:
            event_evidence = _read_jsonl_limited(
                evidence_path,
                limit=limit,
                predicate=lambda item: _event_related_record_matches(
                    item,
                    event_ids=event_ids,
                    track_id=track_id,
                ),
            )
            rule_executions = _read_jsonl_limited(
                executions_path,
                limit=limit,
                predicate=lambda item: _event_related_record_matches(
                    item,
                    event_ids=event_ids,
                    track_id=track_id,
                ),
            )

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "events": events,
            "event_evidence": event_evidence,
            "rule_executions": rule_executions,
            "limit": limit,
            "event_type": event_type,
            "track_id": track_id,
        }

    def read_run_alerts(
        self,
        run_id: str,
        limit: int = 100,
        status: str | None = None,
        level: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "alert_summary.json"
        alerts_path = run_dir / "alerts.jsonl"
        if not summary_path.is_file() or not alerts_path.is_file():
            raise FileNotFoundError("alert artifacts not found")

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        alerts: list[dict[str, Any]] = []
        if limit > 0:
            alerts = _read_jsonl_limited(
                alerts_path,
                limit=limit,
                predicate=lambda item: _alert_matches(
                    item,
                    status=status,
                    level=level,
                    event_type=event_type,
                ),
            )

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "alerts": alerts,
            "limit": limit,
            "status": status,
            "level": level,
            "event_type": event_type,
        }

    def read_run_flow_counts(
        self,
        run_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            rows = FlowCountRepository(db).list(run_id=run_id)
            if rows:
                return {
                    "run_id": run_id,
                    "records": [_model_dict(row) for row in rows],
                    "summary": {"total_records": len(rows)},
                    "source": "db",
                }
        run_dir = self._ensure_statistics_artifacts(run_id)
        flow_counts_path = run_dir / "flow_counts.json"
        if not flow_counts_path.is_file():
            raise FileNotFoundError("flow counts artifact not found")
        with flow_counts_path.open(encoding="utf-8") as file:
            payload = json.load(file)
        payload["source"] = "artifact"
        return payload

    def read_run_zone_statistics(
        self,
        run_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            rows = ZoneStatisticRepository(db).list(run_id=run_id)
            if rows:
                return {
                    "run_id": run_id,
                    "windows": [_model_dict(row) for row in rows],
                    "summary": {"total_windows": len(rows)},
                    "source": "db",
                }
        run_dir = self._ensure_statistics_artifacts(run_id)
        zone_statistics_path = run_dir / "zone_statistics.json"
        if not zone_statistics_path.is_file():
            raise FileNotFoundError("zone statistics artifact not found")
        with zone_statistics_path.open(encoding="utf-8") as file:
            payload = json.load(file)
        payload["source"] = "artifact"
        return payload

    def read_run_manifest(
        self,
        run_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        if db is not None:
            run = TrafficAnalysisRunRepository(db).get(run_id)
            if run is not None:
                return _db_run_manifest(run)
        metadata = self._load_metadata(run_id)
        writer = TrafficArtifactWriter(self._run_dir(run_id).parent)
        return writer.write_run_manifest(
            run_id,
            status=str(metadata.get("status") or "completed"),
        )

    def clear(self) -> None:
        self._runs.clear()

    def _run_dir(self, run_id: str) -> Path:
        return self._results_dir() / run_id

    def _results_dir(self) -> Path:
        from app.core.config import get_settings

        return get_settings().results_dir

    def _load_metadata(self, run_id: str) -> dict[str, Any]:
        metadata_path = self._run_dir(run_id) / "metadata.json"
        if not metadata_path.is_file():
            raise KeyError(run_id)
        with metadata_path.open(encoding="utf-8") as file:
            return json.load(file)

    def _ensure_statistics_artifacts(self, run_id: str) -> Path:
        metadata = self._load_metadata(run_id)
        run_dir = self._run_dir(run_id)
        writer = TrafficArtifactWriter(run_dir.parent)
        if not (run_dir / "flow_counts.json").is_file() or not (
            run_dir / "zone_statistics.json"
        ).is_file():
            writer.write_statistics_outputs(run_id)
        else:
            writer.write_run_manifest(
                run_id,
                status=str(metadata.get("status") or "completed"),
            )
        return run_dir


traffic_analysis_service = TrafficAnalysisService()


def _db_run_summary(run: TrafficAnalysisRun) -> dict[str, Any]:
    artifact_paths = {
        str(key): _safe_relative_path(value)
        for key, value in (run.artifact_index or {}).items()
        if value
    }
    summary = run.summary or {}
    artifact_summary = summary.get("artifact_summary")
    if not isinstance(artifact_summary, dict):
        artifact_summary = {
            key: {
                "status": "available",
                "path": path,
                "record_count": 0,
            }
            for key, path in artifact_paths.items()
        }
    return {
        "id": run.id,
        "run_id": run.id,
        "video_id": run.video_id,
        "status": run.status,
        "mode": str(summary.get("mode") or "offline"),
        "result_dir": _public_result_dir(run.id, run.result_dir),
        "created_at": _to_iso(run.created_at),
        "updated_at": _to_iso(run.updated_at),
        "started_at": str(summary.get("started_at") or ""),
        "finished_at": str(summary.get("finished_at") or ""),
        "source": "db",
        "schema_version": STAGE6D_SCHEMA_VERSION,
        "metadata": {
            "available": bool(summary),
            "path": "db",
            "status": "available" if summary else "empty",
        },
        "manifest": {
            "available": True,
            "path": "db",
            "status": "available",
            "schema_version": summary.get("schema_version"),
        },
        "artifact_index": {
            "available": bool(artifact_paths),
            "path": "db",
            "status": "available" if artifact_paths else "empty",
        },
        "artifact_paths": artifact_paths,
        "artifact_summary": artifact_summary,
    }


def _db_run_manifest(run: TrafficAnalysisRun) -> dict[str, Any]:
    artifacts = {
        key: {
            "status": "available",
            "path": _safe_relative_path(path),
            "record_count": 0,
        }
        for key, path in (run.artifact_index or {}).items()
    }
    return {
        "schema_version": "stage6b.v1",
        "run_id": run.id,
        "video_id": run.video_id,
        "status": run.status,
        "created_at": _to_iso(run.created_at),
        "updated_at": _to_iso(run.updated_at),
        "result_dir": _public_result_dir(run.id, run.result_dir),
        "artifacts": artifacts,
        "source": "db",
    }


def _db_result_summary(db: Session, run_id: str) -> dict[str, Any]:
    run = TrafficAnalysisRunRepository(db).get(run_id)
    if run is None:
        return {}
    return run.summary or {}


def _first_row_video_id(rows: list[Any]) -> str:
    for row in rows:
        video_id = getattr(row, "video_id", None)
        if video_id:
            return str(video_id)
    return ""


def _group_result_rows(rows: list[Any], item_key: str) -> list[dict[str, Any]]:
    frames_by_index: dict[int, dict[str, Any]] = {}
    for row in rows:
        frame_index = int(getattr(row, "frame_index", 0) or 0)
        frame = frames_by_index.setdefault(
            frame_index,
            {
                "frame_index": frame_index,
                "timestamp_ms": getattr(row, "timestamp_ms", None),
                item_key: [],
            },
        )
        frame[item_key].append(_model_dict(row))
    return [frames_by_index[index] for index in sorted(frames_by_index)]


def _model_dict(row: Any) -> dict[str, Any]:
    payload = {
        attr.key: _jsonable_value(getattr(row, attr.key))
        for attr in row.__mapper__.column_attrs
    }
    if "metadata_json" in payload:
        payload["metadata"] = payload.pop("metadata_json")
    return payload


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _to_iso(value)
    return value


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value or "")


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    public = dict(metadata)
    input_video = public.get("input_video")
    if input_video:
        public["input_video"] = Path(str(input_video)).name
    return public


def _load_json_state(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    state = {
        "available": False,
        "path": path.name,
        "status": "missing",
    }
    if not path.is_file():
        return {}, state
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        state["status"] = "error"
        state["error"] = str(exc)
        return {}, state
    if not isinstance(payload, dict):
        state["status"] = "error"
        state["error"] = "json payload must be an object"
        return {}, state
    state["available"] = True
    state["status"] = "available"
    return payload, state


def _summary_source(
    *,
    manifest_state: dict[str, Any],
    metadata_state: dict[str, Any],
    artifact_index_state: dict[str, Any],
    registry_run: dict[str, Any] | None,
) -> str:
    if manifest_state["status"] == "available":
        return "manifest"
    if metadata_state["status"] == "available":
        return "metadata"
    if artifact_index_state["status"] == "available":
        return "artifact_index"
    if registry_run is not None:
        return "in_memory_registry"
    return "directory_scan"


def _artifact_summary(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    artifact_index: dict[str, Any],
    registry_run: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    manifest_artifacts = manifest.get("artifacts")
    if isinstance(manifest_artifacts, dict):
        return {
            str(key): _summary_artifact_record(value)
            for key, value in manifest_artifacts.items()
            if isinstance(value, dict)
        }

    metadata_summary = metadata.get("artifact_summary")
    if isinstance(metadata_summary, dict):
        return {
            str(key): _summary_artifact_record(value)
            for key, value in metadata_summary.items()
            if isinstance(value, dict)
        }

    artifact_paths = _artifact_paths(
        metadata=metadata,
        artifact_index=artifact_index,
        registry_run=registry_run,
    )
    return {
        key: {
            "status": "available" if (run_dir / path.rstrip("/")).exists() else "missing",
            "path": path,
            "record_count": 0,
        }
        for key, path in artifact_paths.items()
    }


def _summary_artifact_record(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(value.get("status", "unknown")),
        "path": _safe_relative_path(value.get("path", "")),
        "record_count": int(value.get("record_count") or 0),
    }


def _artifact_paths(
    *,
    metadata: dict[str, Any],
    artifact_index: dict[str, Any],
    registry_run: dict[str, Any] | None,
) -> dict[str, str]:
    indexed = artifact_index.get("artifacts")
    if isinstance(indexed, dict):
        return {
            str(key): _safe_relative_path(value)
            for key, value in indexed.items()
            if value
        }
    metadata_artifacts = metadata.get("artifacts")
    if isinstance(metadata_artifacts, dict):
        return {
            str(key): _safe_relative_path(value)
            for key, value in metadata_artifacts.items()
            if value
        }
    registry_artifacts = _mapping_value(registry_run, "artifact_index")
    if isinstance(registry_artifacts, dict):
        return {
            str(key): _safe_relative_path(value)
            for key, value in registry_artifacts.items()
            if value
        }
    return {}


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return None


def _first_string(*values: Any, default: str) -> str:
    for value in values:
        if value is not None and value != "":
            return str(value)
    return default


def _public_result_dir(run_id: str, value: Any) -> str:
    if value:
        path = Path(str(value))
        if not path.is_absolute() and ".." not in path.parts:
            return str(value)
    return f"results/traffic_analysis/{run_id}"


def _safe_relative_path(value: Any) -> str:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts:
        return path.name
    return str(value)


def _summary_matches(
    summary: dict[str, Any],
    *,
    status: str | None,
    video_id: str | None,
) -> bool:
    if status is not None and summary.get("status") != status:
        return False
    if video_id is not None and summary.get("video_id") != video_id:
        return False
    return True


def _summary_sort_value(summary: dict[str, Any]) -> str:
    for key in ("updated_at", "finished_at", "created_at"):
        value = summary.get(key)
        if value:
            return str(value)
    return ""


def _track_id_matches(value: Any, track_id: int) -> bool:
    try:
        return int(value) == track_id
    except (TypeError, ValueError):
        return False


def _read_jsonl_limited(
    path: Path,
    *,
    limit: int,
    predicate,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not predicate(row):
                continue
            rows.append(row)
            if len(rows) >= limit:
                break
    return rows


def _event_matches(
    event: dict[str, Any],
    *,
    event_type: str | None,
    track_id: int | None,
) -> bool:
    if event_type is not None and event.get("event_type") != event_type:
        return False
    if track_id is not None and not _track_id_matches(event.get("track_id"), track_id):
        return False
    return True


def _event_related_record_matches(
    row: dict[str, Any],
    *,
    event_ids: set[str] | None,
    track_id: int | None,
) -> bool:
    if event_ids is not None:
        event_id = row.get("event_id")
        if event_id is None or str(event_id) not in event_ids:
            return False
    if track_id is not None and not _track_id_matches(row.get("track_id"), track_id):
        return False
    return True


def _alert_matches(
    alert: dict[str, Any],
    *,
    status: str | None,
    level: str | None,
    event_type: str | None,
) -> bool:
    if status is not None and alert.get("status") != status:
        return False
    if level is not None and alert.get("level") != level:
        return False
    if event_type is not None and alert.get("event_type") != event_type:
        return False
    return True
