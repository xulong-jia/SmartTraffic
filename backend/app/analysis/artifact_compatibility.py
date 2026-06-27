from __future__ import annotations

import csv
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import (
    AlertRepository,
    BadCaseRepository,
    DetectionRepository,
    EvaluationDatasetRepository,
    EvaluationResultRepository,
    EventEvidenceRepository,
    EventRepository,
    FlowCountRepository,
    FrameRepository,
    ModelRunRepository,
    RuleExecutionRepository,
    TrackRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
    VideoRepository,
    ZoneStatisticRepository,
)


ARTIFACT_DEFINITIONS = {
    "metadata": "metadata.json",
    "manifest": "manifest.json",
    "artifact_index": "artifact_index.json",
    "detections_csv": "detections.csv",
    "tracks_csv": "tracks.csv",
    "trajectory_points_csv": "trajectory_points.csv",
    "events_jsonl": "events.jsonl",
    "event_evidence_jsonl": "event_evidence.jsonl",
    "rule_executions_jsonl": "rule_executions.jsonl",
    "alerts_jsonl": "alerts.jsonl",
    "flow_counts": "flow_counts.json",
    "zone_statistics": "zone_statistics.json",
    "evaluation_summary": "evaluation_summary.json",
    "bad_cases_jsonl": "bad_cases.jsonl",
    "bad_cases_csv": "bad_cases.csv",
}


@dataclass(frozen=True)
class ArtifactPathStatus:
    key: str
    path: Path
    exists: bool


@dataclass(frozen=True)
class ArtifactDiscovery:
    run_id: str
    run_dir: Path
    paths: dict[str, ArtifactPathStatus]
    existing: list[str]
    missing: list[str]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactImportSummary:
    run_id: str
    dry_run: bool
    planned: dict[str, int]
    imported: dict[str, int]
    skipped: dict[str, int]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "planned": self.planned,
            "imported": self.imported,
            "skipped": self.skipped,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class ReadThroughResult:
    source: str
    items: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ManifestReadThroughResult:
    source: str
    item: dict[str, Any] | None
    warnings: list[str] = field(default_factory=list)


def discover_run_artifacts(
    run_id: str,
    *,
    result_dir: str | Path | None = None,
    results_dir: str | Path | None = None,
) -> ArtifactDiscovery:
    run_dir = _resolve_run_dir(run_id, result_dir=result_dir, results_dir=results_dir)
    warnings: list[str] = []
    metadata = _read_json_safe(run_dir / "metadata.json", warnings)
    artifact_index = _read_json_safe(run_dir / "artifact_index.json", warnings)
    artifact_map = _artifact_map(metadata, artifact_index)

    paths: dict[str, ArtifactPathStatus] = {}
    for key, default_relative_path in ARTIFACT_DEFINITIONS.items():
        relative_path = artifact_map.get(key) or artifact_map.get(_alias_key(key)) or default_relative_path
        path = run_dir / relative_path
        paths[key] = ArtifactPathStatus(key=key, path=path, exists=path.exists())

    existing = sorted(key for key, status in paths.items() if status.exists)
    missing = sorted(key for key, status in paths.items() if not status.exists)
    return ArtifactDiscovery(
        run_id=run_id,
        run_dir=run_dir,
        paths=paths,
        existing=existing,
        missing=missing,
        warnings=warnings,
    )


def import_run_artifacts_to_db(
    session: Session,
    run_id: str,
    result_dir: str | Path,
    *,
    dry_run: bool = False,
) -> ArtifactImportSummary:
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    warnings = list(discovery.warnings)
    metadata = _read_json_safe(discovery.paths["metadata"].path, warnings)
    artifacts = _load_supported_artifacts(discovery, warnings)
    planned = _planned_counts(artifacts)
    planned["videos"] = 1
    planned["runs"] = 1

    imported = _empty_counts()
    skipped = _empty_counts()
    if dry_run:
        return ArtifactImportSummary(
            run_id=run_id,
            dry_run=True,
            planned=planned,
            imported=imported,
            skipped=skipped,
            warnings=warnings,
        )

    video_id = str(metadata.get("video_id") or f"video-{run_id}")
    video_repo = VideoRepository(session)
    if video_repo.get(video_id) is None:
        input_video = str(metadata.get("input_video") or metadata.get("video_path") or video_id)
        video_repo.create(
            id=video_id,
            filename=Path(input_video).name,
            storage_path=input_video,
            status=str(metadata.get("video_status") or "imported"),
            metadata_json=metadata,
        )
        imported["videos"] += 1
    else:
        skipped["videos"] += 1

    run_repo = TrafficAnalysisRunRepository(session)
    if run_repo.get(run_id) is None:
        run_repo.create(
            id=run_id,
            video_id=video_id,
            status=str(metadata.get("status") or "imported"),
            result_dir=str(discovery.run_dir),
            artifact_index={
                key: str(status.path.relative_to(discovery.run_dir))
                for key, status in discovery.paths.items()
                if status.exists
            },
            summary=metadata,
        )
        imported["runs"] += 1
    else:
        skipped["runs"] += 1

    _import_detections(session, run_id, video_id, artifacts["detections"], imported, skipped)
    _import_tracks(session, run_id, video_id, artifacts["tracks"], imported, skipped)
    _import_trajectory_points(session, run_id, video_id, artifacts["trajectory_points"], imported, skipped)
    _import_events(
        session,
        run_id,
        video_id,
        artifacts["events"],
        artifacts["event_evidence"],
        artifacts["rule_executions"],
        imported,
        skipped,
    )
    _import_event_evidence(session, run_id, video_id, artifacts["event_evidence"], imported, skipped)
    _import_rule_executions(session, run_id, artifacts["rule_executions"], imported, skipped)
    _import_alerts(session, run_id, artifacts["alerts"], imported, skipped)
    _import_flow_counts(session, run_id, artifacts["flow_counts"], imported, skipped)
    _import_zone_statistics(session, run_id, artifacts["zone_statistics"], imported, skipped)
    _import_evaluation_summary(session, run_id, artifacts["evaluation_summary"], imported, skipped)
    _import_bad_cases(session, run_id, artifacts["bad_cases"], imported, skipped)

    return ArtifactImportSummary(
        run_id=run_id,
        dry_run=False,
        planned=planned,
        imported=imported,
        skipped=skipped,
        warnings=warnings,
    )


def get_run_manifest_read_through(
    session: Session,
    run_id: str,
    result_dir: str | Path,
) -> ManifestReadThroughResult:
    run = TrafficAnalysisRunRepository(session).get(run_id)
    if run is not None:
        return ManifestReadThroughResult(
            source="db",
            item={
                "run_id": run.id,
                "video_id": run.video_id,
                "status": run.status,
                "result_dir": run.result_dir,
                "artifact_index": run.artifact_index or {},
                "summary": run.summary or {},
            },
        )

    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    manifest = _read_json_safe(discovery.paths["manifest"].path, warnings)
    if manifest:
        return ManifestReadThroughResult(source="artifact", item=manifest, warnings=warnings)
    metadata = _read_json_safe(discovery.paths["metadata"].path, warnings)
    if metadata:
        return ManifestReadThroughResult(source="artifact", item=metadata, warnings=warnings)
    return ManifestReadThroughResult(source="empty", item=None, warnings=warnings or ["run manifest not found"])


def list_detections_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = DetectionRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row, "bbox") for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    items = _read_csv_safe(discovery.paths["detections_csv"].path, warnings)
    return _artifact_result(items, warnings, "detections.csv")


def list_tracks_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = TrackRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row, "metadata_json") for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    items = _read_csv_safe(discovery.paths["tracks_csv"].path, warnings)
    return _artifact_result(items, warnings, "tracks.csv")


def list_events_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = EventRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row, "payload") for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    items = _read_jsonl_safe(discovery.paths["events_jsonl"].path, warnings)
    return _artifact_result(items, warnings, "events.jsonl")


def list_alerts_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = AlertRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row, "payload") for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    items = _read_jsonl_safe(discovery.paths["alerts_jsonl"].path, warnings)
    return _artifact_result(items, warnings, "alerts.jsonl")


def get_flow_counts_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = FlowCountRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row) for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    payload = _read_json_safe(discovery.paths["flow_counts"].path, warnings)
    return _artifact_result(list(payload.get("records", [])) if payload else [], warnings, "flow_counts.json")


def get_zone_statistics_read_through(session: Session, run_id: str, result_dir: str | Path) -> ReadThroughResult:
    rows = ZoneStatisticRepository(session).list(run_id=run_id)
    if rows:
        return ReadThroughResult(source="db", items=[_model_dict(row, "payload") for row in rows])
    warnings: list[str] = []
    discovery = discover_run_artifacts(run_id, result_dir=result_dir)
    payload = _read_json_safe(discovery.paths["zone_statistics"].path, warnings)
    return _artifact_result(list(payload.get("windows", [])) if payload else [], warnings, "zone_statistics.json")


def _resolve_run_dir(
    run_id: str,
    *,
    result_dir: str | Path | None,
    results_dir: str | Path | None,
) -> Path:
    if result_dir is not None:
        candidate = Path(result_dir)
        if candidate.name == run_id or (candidate / "metadata.json").exists():
            return candidate
        return candidate / run_id
    if results_dir is not None:
        return Path(results_dir) / run_id
    return Path("results/traffic_analysis") / run_id


def _artifact_map(metadata: dict[str, Any], artifact_index: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for source in (metadata.get("artifacts"), artifact_index.get("artifacts")):
        if isinstance(source, dict):
            mapping.update({str(key): str(value) for key, value in source.items()})
    return mapping


def _alias_key(key: str) -> str:
    aliases = {
        "bad_cases_jsonl": "bad_cases",
        "detections_csv": "detections",
        "tracks_csv": "tracks",
        "trajectory_points_csv": "trajectory_points",
        "events_jsonl": "events",
        "event_evidence_jsonl": "event_evidence",
        "rule_executions_jsonl": "rule_executions",
        "alerts_jsonl": "alerts",
    }
    return aliases.get(key, key)


def _load_supported_artifacts(
    discovery: ArtifactDiscovery,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "detections": _read_csv_safe(discovery.paths["detections_csv"].path, warnings),
        "tracks": _read_csv_safe(discovery.paths["tracks_csv"].path, warnings),
        "trajectory_points": _read_csv_safe(discovery.paths["trajectory_points_csv"].path, warnings),
        "events": _read_jsonl_safe(discovery.paths["events_jsonl"].path, warnings),
        "event_evidence": _read_jsonl_safe(discovery.paths["event_evidence_jsonl"].path, warnings),
        "rule_executions": _read_jsonl_safe(discovery.paths["rule_executions_jsonl"].path, warnings),
        "alerts": _read_jsonl_safe(discovery.paths["alerts_jsonl"].path, warnings),
        "flow_counts": _read_json_safe(discovery.paths["flow_counts"].path, warnings).get("records", []),
        "zone_statistics": _read_json_safe(discovery.paths["zone_statistics"].path, warnings).get("windows", []),
        "evaluation_summary": _read_json_safe(discovery.paths["evaluation_summary"].path, warnings),
        "bad_cases": _read_bad_cases(discovery, warnings),
    }


def _read_bad_cases(discovery: ArtifactDiscovery, warnings: list[str]) -> list[dict[str, Any]]:
    jsonl_path = discovery.paths["bad_cases_jsonl"].path
    if jsonl_path.is_file():
        return _read_jsonl_safe(jsonl_path, warnings)
    return _read_csv_safe(discovery.paths["bad_cases_csv"].path, warnings)


def _planned_counts(artifacts: dict[str, Any]) -> dict[str, int]:
    counts = _empty_counts()
    counts.update(
        {
            "detections": len(artifacts["detections"]),
            "tracks": len(artifacts["tracks"]),
            "trajectory_points": len(artifacts["trajectory_points"]),
            "events": len(artifacts["events"]),
            "event_evidence": len(artifacts["event_evidence"]),
            "rule_executions": len(artifacts["rule_executions"]),
            "alerts": len(artifacts["alerts"]),
            "flow_counts": len(artifacts["flow_counts"]),
            "zone_statistics": len(artifacts["zone_statistics"]),
            "evaluation_results": 1 if artifacts["evaluation_summary"] else 0,
            "bad_cases": len(artifacts["bad_cases"]),
        }
    )
    return counts


def _empty_counts() -> dict[str, int]:
    return {
        "videos": 0,
        "runs": 0,
        "detections": 0,
        "tracks": 0,
        "trajectory_points": 0,
        "events": 0,
        "event_evidence": 0,
        "rule_executions": 0,
        "alerts": 0,
        "flow_counts": 0,
        "zone_statistics": 0,
        "evaluation_results": 0,
        "bad_cases": 0,
    }


def _import_detections(
    session: Session,
    run_id: str,
    video_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = DetectionRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = _row_id("det", run_id, row, index, "detection_id")
        if repo.get(item_id) is not None:
            skipped["detections"] += 1
            continue
        repo.create(
            id=item_id,
            run_id=run_id,
            video_id=str(row.get("video_id") or video_id),
            frame_index=_int(row.get("frame_index"), 0),
            class_name=str(row.get("class_name") or row.get("label") or "unknown"),
            confidence=_float_or_none(row.get("confidence")),
            bbox={
                "x1": _float_or_none(row.get("x1")),
                "y1": _float_or_none(row.get("y1")),
                "x2": _float_or_none(row.get("x2")),
                "y2": _float_or_none(row.get("y2")),
            },
            track_id=_str_or_none(row.get("track_id")),
        )
        imported["detections"] += 1


def _import_tracks(
    session: Session,
    run_id: str,
    video_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = TrackRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = _row_id("track", run_id, row, index, "track_row_id")
        if repo.get(item_id) is not None:
            skipped["tracks"] += 1
            continue
        frame_index = _int(row.get("frame_index"), 0)
        repo.create(
            id=item_id,
            run_id=run_id,
            video_id=str(row.get("video_id") or video_id),
            track_id=str(row.get("track_id") or item_id),
            class_name=_str_or_none(row.get("class_name")),
            start_frame=_int(row.get("start_frame"), frame_index),
            end_frame=_int(row.get("end_frame"), frame_index),
            confidence=_float_or_none(row.get("confidence")),
            metadata_json=row,
        )
        imported["tracks"] += 1


def _import_trajectory_points(
    session: Session,
    run_id: str,
    video_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = TrajectoryPointRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = _row_id("traj", run_id, row, index, "trajectory_point_id")
        if repo.get(item_id) is not None:
            skipped["trajectory_points"] += 1
            continue
        repo.create(
            id=item_id,
            run_id=run_id,
            video_id=str(row.get("video_id") or video_id),
            track_id=str(row.get("track_id") or "unknown"),
            frame_index=_int(row.get("frame_index"), 0),
            timestamp_ms=_float_or_none(row.get("timestamp_ms")),
            x=_float(row.get("x") or row.get("center_x") or row.get("bottom_center_x"), 0.0),
            y=_float(row.get("y") or row.get("center_y") or row.get("bottom_center_y"), 0.0),
            speed=_float_or_none(row.get("speed_px_per_second") or row.get("speed")),
            direction=_str_or_none(row.get("direction") or row.get("moving_angle")),
            features=row,
        )
        imported["trajectory_points"] += 1


def _import_events(
    session: Session,
    run_id: str,
    video_id: str,
    rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    rule_execution_rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = EventRepository(session)
    evidence_by_event_id = _first_row_by_event_id(evidence_rows)
    execution_by_event_id = _first_row_by_event_id(rule_execution_rows)
    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("event_id") or _row_id("event", run_id, row, index))
        if repo.get(item_id) is not None:
            skipped["events"] += 1
            continue
        related_evidence = evidence_by_event_id.get(item_id, {})
        related_execution = execution_by_event_id.get(item_id, {})
        repo.create(
            id=item_id,
            run_id=run_id,
            video_id=str(row.get("video_id") or video_id),
            rule_id=_str_or_none(
                row.get("rule_id")
                or _nested(row, "evidence", "rule_id")
                or related_evidence.get("rule_id")
                or related_execution.get("rule_id")
            ),
            zone_id=_str_or_none(
                row.get("zone_id")
                or _nested(row, "evidence", "zone_id")
                or related_evidence.get("zone_id")
                or related_execution.get("zone_id")
            ),
            type=str(row.get("event_type") or row.get("type") or "unknown"),
            status=str(row.get("status") or "new"),
            severity=_str_or_none(row.get("severity")),
            frame_index=_int_or_none(_first_present(row.get("frame_index"), row.get("start_frame"))),
            timestamp_ms=_float_or_none(_first_present(row.get("timestamp_ms"), row.get("start_time_ms"))),
            track_id=_str_or_none(row.get("track_id")),
            payload=row,
        )
        imported["events"] += 1


def _import_event_evidence(
    session: Session,
    run_id: str,
    video_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = EventEvidenceRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("evidence_id") or row.get("id") or _row_id("evidence", run_id, row, index))[:64]
        event_id = _str_or_none(row.get("event_id"))
        if event_id is None:
            skipped["event_evidence"] += 1
            continue
        if repo.get(item_id) is not None:
            skipped["event_evidence"] += 1
            continue
        payload = dict(row)
        payload.setdefault("video_id", video_id)
        payload.setdefault("track_id", row.get("track_id"))
        payload.setdefault("frame_index", _int_or_none(row.get("frame_index")))
        payload.setdefault("timestamp_ms", _float_or_none(row.get("timestamp_ms")))
        payload.setdefault("event_type", row.get("event_type") or row.get("type"))
        payload.setdefault("zone_id", row.get("zone_id"))
        payload.setdefault("rule_id", row.get("rule_id"))
        payload.setdefault("evidence_json", row.get("evidence_json") or row.get("payload") or {})
        payload.setdefault("snapshot_path", row.get("snapshot_path"))
        repo.create(
            id=item_id,
            event_id=event_id,
            run_id=str(row.get("run_id") or run_id),
            evidence_type=str(row.get("evidence_type") or "event_evidence"),
            payload=payload,
            artifact_path=_str_or_none(payload.get("snapshot_path")),
        )
        imported["event_evidence"] += 1


def _import_rule_executions(
    session: Session,
    run_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = RuleExecutionRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("execution_id") or row.get("id") or _row_id("rule-exec", run_id, row, index))[:64]
        if repo.get(item_id) is not None:
            skipped["rule_executions"] += 1
            continue
        details = dict(row)
        input_features = row.get("input_features") if isinstance(row.get("input_features"), dict) else {}
        output_result = row.get("output_result") if isinstance(row.get("output_result"), dict) else {}
        details.setdefault("event_id", row.get("event_id"))
        details.setdefault("track_id", row.get("track_id"))
        details.setdefault("frame_index", _int_or_none(row.get("frame_index")))
        details.setdefault("input_features", input_features)
        details.setdefault("output_result", output_result)
        status = str(row.get("status") or "unknown")
        repo.create(
            id=item_id,
            run_id=str(row.get("run_id") or run_id),
            rule_id=_str_or_none(row.get("rule_id")),
            status=status,
            matched_count=_int(row.get("matched_count"), 1 if status == "matched" else 0),
            details=details,
            error_message=_str_or_none(row.get("error_message") or output_result.get("error")),
        )
        imported["rule_executions"] += 1


def _import_alerts(
    session: Session,
    run_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = AlertRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("alert_id") or _row_id("alert", run_id, row, index))
        if repo.get(item_id) is not None:
            skipped["alerts"] += 1
            continue
        repo.create(
            id=item_id,
            run_id=run_id,
            event_id=_str_or_none(row.get("event_id")),
            type=str(row.get("alert_type") or row.get("type") or "unknown"),
            status=str(row.get("status") or "new"),
            severity=_str_or_none(row.get("severity")),
            message=_str_or_none(row.get("message")),
            payload=row,
        )
        imported["alerts"] += 1


def _import_flow_counts(
    session: Session,
    run_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = FlowCountRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = _row_id("flow", run_id, row, index, "flow_count_id")
        if repo.get(item_id) is not None:
            skipped["flow_counts"] += 1
            continue
        repo.create(
            id=item_id,
            run_id=run_id,
            zone_id=None,
            line_id=_str_or_none(row.get("counting_line_id") or row.get("line_id")),
            class_name=_str_or_none(row.get("class_name")),
            direction=_str_or_none(row.get("direction")),
            count=_int(row.get("total_count") or row.get("count"), 1),
        )
        imported["flow_counts"] += 1


def _import_zone_statistics(
    session: Session,
    run_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = ZoneStatisticRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = _row_id("zone-stat", run_id, row, index, "zone_statistic_id")
        if repo.get(item_id) is not None:
            skipped["zone_statistics"] += 1
            continue
        metric_value = _float_or_none(
            row.get("vehicle_count")
            or row.get("avg_speed_px_per_frame")
            or row.get("metric_value")
        )
        repo.create(
            id=item_id,
            run_id=run_id,
            zone_id=None,
            metric_name=str(row.get("metric_name") or "zone_window"),
            metric_value=metric_value,
            payload=row,
        )
        imported["zone_statistics"] += 1


def _import_evaluation_summary(
    session: Session,
    run_id: str,
    payload: dict[str, Any],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    if not payload:
        return
    dataset_id = f"artifact-dataset-{run_id}"[:64]
    dataset_repo = EvaluationDatasetRepository(session)
    if dataset_repo.get(dataset_id) is None:
        dataset_repo.create(
            id=dataset_id,
            name=f"Artifact summary {run_id}",
            dataset_type="artifact_summary",
            version="stage1ef",
            status="imported",
            config={"source": "evaluation_summary.json"},
        )
    result_id = f"artifact-eval-{run_id}"[:64]
    result_repo = EvaluationResultRepository(session)
    if result_repo.get(result_id) is not None:
        skipped["evaluation_results"] += 1
        return
    result_repo.create(
        id=result_id,
        dataset_id=dataset_id,
        run_id=run_id,
        evaluation_type="artifact_summary",
        status="imported",
        metrics=payload.get("summary") or payload,
        summary=payload,
    )
    imported["evaluation_results"] += 1


def _import_bad_cases(
    session: Session,
    run_id: str,
    rows: list[dict[str, Any]],
    imported: dict[str, int],
    skipped: dict[str, int],
) -> None:
    repo = BadCaseRepository(session)
    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("case_id") or row.get("bad_case_id") or _row_id("bad", run_id, row, index))
        if repo.get(item_id) is not None:
            skipped["bad_cases"] += 1
            continue
        repo.create(
            id=item_id,
            run_id=run_id,
            event_id=_str_or_none(row.get("event_id")),
            type=str(row.get("case_type") or row.get("type") or "unknown"),
            status=str(row.get("status") or "open"),
            severity=_str_or_none(row.get("severity")),
            description=_str_or_none(row.get("description")),
            tags=row.get("tags") if isinstance(row.get("tags"), list) else _parse_json_value(row.get("tags"), []),
            payload=row,
        )
        imported["bad_cases"] += 1


def _read_json_safe(path: Path, warnings: list[str]) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warnings.append(f"{path.name}: invalid JSON at line {exc.lineno}")
        return {}
    if not isinstance(payload, dict):
        warnings.append(f"{path.name}: expected JSON object")
        return {}
    return payload


def _read_jsonl_safe(path: Path, warnings: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"{path.name}: invalid JSONL at line {line_number}")
                continue
            if isinstance(payload, dict):
                rows.append(payload)
            else:
                warnings.append(f"{path.name}: expected object at line {line_number}")
    return rows


def _read_csv_safe(path: Path, warnings: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as file:
            return [dict(row) for row in csv.DictReader(file)]
    except csv.Error as exc:
        warnings.append(f"{path.name}: invalid CSV: {exc}")
        return []


def _artifact_result(items: list[dict[str, Any]], warnings: list[str], artifact_name: str) -> ReadThroughResult:
    if items:
        return ReadThroughResult(source="artifact", items=items, warnings=warnings)
    if warnings:
        return ReadThroughResult(source="artifact", items=[], warnings=warnings)
    return ReadThroughResult(source="empty", items=[], warnings=[f"{artifact_name} not found"])


def _model_dict(row: Any, *json_fields: str) -> dict[str, Any]:
    payload = {
        attr.key: getattr(row, attr.key)
        for attr in row.__mapper__.column_attrs
    }
    for field_name in json_fields:
        if field_name == "metadata_json":
            payload["metadata"] = payload.pop("metadata_json", None)
    return payload


def _row_id(prefix: str, run_id: str, row: dict[str, Any], index: int, *preferred_fields: str) -> str:
    for field_name in preferred_fields:
        value = row.get(field_name)
        if value:
            return str(value)[:64]
    return f"{prefix}-{run_id}-{index}"[:64]


def _int(value: Any, default: int) -> int:
    parsed = _int_or_none(value)
    return default if parsed is None else parsed


def _int_or_none(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any, default: float) -> float:
    parsed = _float_or_none(value)
    return default if parsed is None else parsed


def _float_or_none(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _nested(row: dict[str, Any], *keys: str) -> Any:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _first_row_by_event_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_event_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        event_id = row.get("event_id")
        if event_id is not None:
            by_event_id.setdefault(str(event_id), row)
    return by_event_id


def _parse_json_value(value: Any, default: Any) -> Any:
    if value in {None, ""}:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default
