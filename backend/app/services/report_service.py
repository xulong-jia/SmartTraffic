from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.analysis.export import (
    REPORT_EXPORT_HEADERS,
    REPORT_EXPORT_SECTIONS,
    report_pdf,
    report_csv,
    sanitize_report_payload,
)
from app.core.config import get_settings
from app.core.paths import PROJECT_DIR
from app.repositories import TrafficAnalysisRunRepository
from app.services.alert_service import AlertService
from app.services.bad_case_service import BadCaseService
from app.services.evaluation_service import EvaluationService
from app.services.event_lifecycle_service import EventLifecycleService
from app.services.traffic_analysis_service import traffic_analysis_service


NOT_FOR_ENFORCEMENT_NOTE = (
    "SmartTraffic reports are for analysis and review only; not for traffic enforcement."
)

REPORT_BUNDLE_SECTIONS = [
    "summary",
    "events",
    "alerts",
    "flow_counts",
    "zone_statistics",
    "bad_cases",
    "evaluation_results",
    "keyframes",
    "annotated_video",
]


class ReportService:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def list_runs(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return traffic_analysis_service.list_runs(
            limit=limit,
            offset=offset,
            db=self.session,
        )

    def build_summary(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        sections = self._collect_sections(run_id)
        counts = self._build_counts(run, sections)
        keyframe_summary = self._keyframe_summary(run_id, run)
        annotated_video = self._annotated_video_summary(run)
        bundle = self._bundle_summary(
            run_id=run_id,
            run=run,
            counts=counts,
            keyframe_summary=keyframe_summary,
            annotated_video=annotated_video,
        )
        return sanitize_report_payload(
            {
                "run_id": run_id,
                "run": run,
                "counts": counts,
                "artifact_index": run.get("artifact_index", {}),
                "artifact_summary": run.get("artifact_summary", {}),
                "top_event_types": dict(Counter(_event_type(row) for row in sections["events"])),
                "alert_status_counts": dict(Counter(_status(row) for row in sections["alerts"])),
                "flow_totals": _flow_totals(sections["flow_counts"]),
                "bad_case_status_counts": dict(Counter(_status(row) for row in sections["bad_cases"])),
                "bad_case_type_counts": dict(Counter(_bad_case_type(row) for row in sections["bad_cases"])),
                "evaluation_metric_summary": _evaluation_metric_summary(
                    sections["evaluation_results"]
                ),
                "available_exports": list(REPORT_EXPORT_SECTIONS),
                "bundle": bundle,
                "keyframe_summary": keyframe_summary,
                "annotated_video": annotated_video,
                "note": NOT_FOR_ENFORCEMENT_NOTE,
            }
        )

    def build_json_report(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        sections = self._collect_sections(run_id)
        return sanitize_report_payload(
            {
                "metadata": {
                    "generated_at": _utc_now_iso(),
                    "schema_version": "full_stage_6ab.report.v1",
                    "note": NOT_FOR_ENFORCEMENT_NOTE,
                    "available_exports": list(REPORT_EXPORT_SECTIONS),
                },
                "run": run,
                "events": sections["events"],
                "alerts": sections["alerts"],
                "flow_counts": sections["flow_counts"],
                "zone_statistics": sections["zone_statistics"],
                "bad_cases": sections["bad_cases"],
                "evaluation_results": sections["evaluation_results"],
            }
        )

    def build_csv(self, run_id: str, section: str) -> str:
        if section not in REPORT_EXPORT_HEADERS:
            raise ValueError(section)
        self._get_run(run_id)
        sections = self._collect_sections(run_id)
        return report_csv(section, sections[section])

    def build_bundle(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        sections = self._collect_sections(run_id)
        counts = self._build_counts(run, sections)
        keyframe_summary = self._keyframe_summary(run_id, run)
        annotated_video = self._annotated_video_summary(run)
        return sanitize_report_payload(
            self._bundle_summary(
                run_id=run_id,
                run=run,
                counts=counts,
                keyframe_summary=keyframe_summary,
                annotated_video=annotated_video,
            )
        )

    def build_pdf(self, run_id: str) -> bytes:
        summary = self.build_summary(run_id)
        return report_pdf(_pdf_lines(summary))

    def _get_run(self, run_id: str) -> dict[str, Any]:
        return traffic_analysis_service.get_run(run_id, db=self.session)

    def _collect_sections(self, run_id: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "events": self._events(run_id),
            "alerts": self._alerts(run_id),
            "flow_counts": self._flow_counts(run_id),
            "zone_statistics": self._zone_statistics(run_id),
            "bad_cases": self._bad_cases(run_id),
            "evaluation_results": self._evaluation_results(run_id),
        }

    def _events(self, run_id: str) -> list[dict[str, Any]]:
        try:
            payload = traffic_analysis_service.read_run_events(
                run_id,
                limit=1000,
                db=self.session,
            )
            return [dict(item) for item in payload.get("events", [])]
        except (FileNotFoundError, KeyError):
            return []

    def _alerts(self, run_id: str) -> list[dict[str, Any]]:
        if self.session is not None:
            lifecycle = EventLifecycleService(self.session)
            db_alerts = lifecycle.list_alerts(run_id=run_id)
            if db_alerts or TrafficAnalysisRunRepository(self.session).get(run_id) is not None:
                return [dict(item) for item in db_alerts]
        try:
            return [dict(item) for item in AlertService().list_alerts(run_id=run_id)]
        except (FileNotFoundError, KeyError):
            return []

    def _flow_counts(self, run_id: str) -> list[dict[str, Any]]:
        try:
            payload = traffic_analysis_service.read_run_flow_counts(
                run_id,
                db=self.session,
            )
            return [dict(item) for item in payload.get("records", [])]
        except (FileNotFoundError, KeyError):
            return []

    def _zone_statistics(self, run_id: str) -> list[dict[str, Any]]:
        try:
            payload = traffic_analysis_service.read_run_zone_statistics(
                run_id,
                db=self.session,
            )
            return [dict(item) for item in payload.get("windows", [])]
        except (FileNotFoundError, KeyError):
            return []

    def _bad_cases(self, run_id: str) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in BadCaseService(session=self.session).list_bad_cases(run_id=run_id)
        ]

    def _evaluation_results(self, run_id: str) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in EvaluationService(session=self.session).list_results(
                run_id=run_id
            )
        ]

    def _build_counts(
        self,
        run: dict[str, Any],
        sections: dict[str, list[dict[str, Any]]],
    ) -> dict[str, int]:
        result_summary = run.get("artifact_summary")
        return {
            "detections_count": _artifact_count(result_summary, "detections"),
            "tracks_count": _artifact_count(result_summary, "tracks"),
            "trajectory_points_count": _artifact_count(result_summary, "trajectory_points"),
            "events_count": len(sections["events"]),
            "alerts_count": len(sections["alerts"]),
            "flow_count_records": len(sections["flow_counts"]),
            "zone_statistics_records": len(sections["zone_statistics"]),
            "bad_cases_count": len(sections["bad_cases"]),
            "evaluation_results_count": len(sections["evaluation_results"]),
        }

    def _bundle_summary(
        self,
        *,
        run_id: str,
        run: dict[str, Any],
        counts: dict[str, int],
        keyframe_summary: dict[str, Any],
        annotated_video: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "full_stage_6cd.report_bundle.v1",
            "run_id": run_id,
            "generated_at": _utc_now_iso(),
            "included_sections": list(REPORT_BUNDLE_SECTIONS),
            "artifact_references": _artifact_references(
                run=run,
                counts=counts,
                keyframe_summary=keyframe_summary,
                annotated_video=annotated_video,
            ),
            "disclaimer": NOT_FOR_ENFORCEMENT_NOTE,
            "note": (
                "This endpoint returns report bundle metadata only. It does not "
                "create a zip file, copy videos, or embed keyframe images."
            ),
        }

    def _keyframe_summary(self, run_id: str, run: dict[str, Any]) -> dict[str, Any]:
        artifact_summary = _artifact_summary_item(run, "keyframes")
        index_summary = _artifact_summary_item(run, "keyframes_index")
        index_payload = _load_keyframe_index(run_id, run)
        items = [
            _keyframe_item(item)
            for item in index_payload.get("items", [])
            if isinstance(item, dict)
        ]
        status = str(
            index_payload.get("status")
            or artifact_summary.get("status")
            or "missing"
        )
        keyframe_count = len(items)
        if keyframe_count == 0:
            keyframe_count = _int_value(artifact_summary.get("record_count"))
        return {
            "available": status == "available",
            "status": status,
            "keyframe_count": keyframe_count,
            "keyframe_items": items[:50],
            "index_status": index_summary.get("status") or "missing",
            "index_reference": _artifact_path(run, "keyframes_index", "keyframes/index.json"),
            "notes": _visual_notes("keyframes", status),
        }

    def _annotated_video_summary(self, run: dict[str, Any]) -> dict[str, Any]:
        artifact_summary = _artifact_summary_item(run, "annotated_video")
        status = str(artifact_summary.get("status") or "missing")
        reference = _artifact_path(run, "annotated_video", "annotated_video.mp4")
        return {
            "available": status == "available",
            "status": status,
            "annotated_video_available": status == "available",
            "annotated_video_reference": reference,
            "record_count": _int_value(artifact_summary.get("record_count")),
            "notes": _visual_notes("annotated_video", status),
        }


def _artifact_count(summary: Any, key: str) -> int:
    if not isinstance(summary, dict):
        return 0
    item = summary.get(key) or summary.get(f"{key}_jsonl") or summary.get(f"{key}_csv")
    if isinstance(item, dict):
        value = item.get("record_count")
        if isinstance(value, int):
            return value
    return 0


def _event_type(row: dict[str, Any]) -> str:
    return str(row.get("event_type") or row.get("type") or "unknown")


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or "unknown")


def _bad_case_type(row: dict[str, Any]) -> str:
    return str(row.get("case_type") or row.get("type") or "unknown")


def _flow_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    by_direction: Counter[str] = Counter()
    for row in rows:
        count = _int_value(row.get("count"))
        total += count
        by_direction[str(row.get("direction") or "unknown")] += count
    return {"total_count": total, "by_direction": dict(by_direction)}


def _evaluation_metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(row.get("metric_name") or row.get("evaluation_result_id")): row.get("metric_value")
        for row in rows
    }


def _int_value(value: Any) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _artifact_references(
    *,
    run: dict[str, Any],
    counts: dict[str, int],
    keyframe_summary: dict[str, Any],
    annotated_video: dict[str, Any],
) -> list[dict[str, Any]]:
    references = [
        {
            "key": "summary",
            "artifact_type": "virtual_report_section",
            "path": None,
            "exists": True,
            "note": "Run summary is generated from DB rows and artifact metadata.",
        }
    ]
    for section, count_key in [
        ("events", "events_count"),
        ("alerts", "alerts_count"),
        ("flow_counts", "flow_count_records"),
        ("zone_statistics", "zone_statistics_records"),
        ("bad_cases", "bad_cases_count"),
        ("evaluation_results", "evaluation_results_count"),
    ]:
        references.append(
            {
                "key": section,
                "artifact_type": "report_section",
                "path": _artifact_path(run, section, None),
                "exists": counts.get(count_key, 0) > 0,
                "note": f"{counts.get(count_key, 0)} rows available for export.",
            }
        )
    references.append(
        {
            "key": "keyframes",
            "artifact_type": "visual_artifact_reference",
            "path": keyframe_summary.get("index_reference"),
            "exists": bool(keyframe_summary.get("keyframe_count")),
            "note": keyframe_summary.get("notes"),
        }
    )
    references.append(
        {
            "key": "annotated_video",
            "artifact_type": "visual_artifact_reference",
            "path": annotated_video.get("annotated_video_reference"),
            "exists": bool(annotated_video.get("available")),
            "note": annotated_video.get("notes"),
        }
    )
    return references


def _artifact_summary_item(run: dict[str, Any], key: str) -> dict[str, Any]:
    summary = run.get("artifact_summary")
    if isinstance(summary, dict) and isinstance(summary.get(key), dict):
        return dict(summary[key])
    return {}


def _artifact_path(run: dict[str, Any], key: str, fallback: str | None) -> str | None:
    paths = run.get("artifact_paths")
    if isinstance(paths, dict) and paths.get(key):
        return str(paths[key])
    item = _artifact_summary_item(run, key)
    if item.get("path"):
        return str(item["path"])
    return fallback


def _load_keyframe_index(run_id: str, run: dict[str, Any]) -> dict[str, Any]:
    for run_dir in _candidate_run_dirs(run_id, run):
        index_path = run_dir / "keyframes" / "index.json"
        if not index_path.is_file():
            continue
        try:
            with index_path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {"status": "error", "items": []}
        if isinstance(payload, dict):
            return payload
    return {}


def _candidate_run_dirs(run_id: str, run: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    result_dir = run.get("result_dir")
    if result_dir:
        result_path = Path(str(result_dir))
        if result_path.is_absolute():
            candidates.append(result_path)
        elif ".." not in result_path.parts:
            candidates.append(PROJECT_DIR / result_path)
    candidates.append(get_settings().results_dir / run_id)
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _keyframe_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": item.get("source_type"),
        "source_id": item.get("source_id"),
        "frame_index": item.get("frame_index"),
        "timestamp_ms": item.get("timestamp_ms"),
        "path": item.get("path"),
        "status": item.get("status") or "unknown",
    }


def _visual_notes(kind: str, status: str) -> str:
    if status == "available":
        return f"{kind} artifact is available as a relative local artifact reference."
    if status == "missing_source_video":
        return "Source video was not available when visual artifacts were built."
    if status in {"missing", "planned"}:
        return f"{kind} artifact has not been generated for this run."
    if status == "empty":
        return f"{kind} artifact exists but contains no reportable records."
    if status == "error":
        return f"{kind} artifact metadata could not be read."
    return f"{kind} artifact status is {status}."


def _pdf_lines(summary: dict[str, Any]) -> list[str]:
    run = summary.get("run", {})
    counts = summary.get("counts", {})
    bundle = summary.get("bundle", {})
    keyframes = summary.get("keyframe_summary", {})
    annotated_video = summary.get("annotated_video", {})
    lines = [
        "SmartTraffic Analysis Report",
        "",
        "This report is for analysis and review only.",
        "It is not a traffic enforcement document.",
        "Metrics depend on available annotations and configuration.",
        "",
        f"Run ID: {summary.get('run_id')}",
        f"Video ID: {run.get('video_id') or '-'}",
        f"Run status: {run.get('status') or '-'}",
        f"Generated at: {bundle.get('generated_at') or _utc_now_iso()}",
        "",
        "Event summary",
        f"- Events: {counts.get('events_count', 0)}",
        f"- Top event types: {summary.get('top_event_types', {})}",
        "",
        "Alert summary",
        f"- Alerts: {counts.get('alerts_count', 0)}",
        f"- Alert statuses: {summary.get('alert_status_counts', {})}",
        "",
        "Flow summary",
        f"- Flow records: {counts.get('flow_count_records', 0)}",
        f"- Flow totals: {summary.get('flow_totals', {})}",
        "",
        "Zone statistics summary",
        f"- Zone statistic records: {counts.get('zone_statistics_records', 0)}",
        "",
        "Bad case summary",
        f"- Bad cases: {counts.get('bad_cases_count', 0)}",
        f"- Bad case statuses: {summary.get('bad_case_status_counts', {})}",
        "",
        "Evaluation summary",
        f"- Evaluation results: {counts.get('evaluation_results_count', 0)}",
        f"- Evaluation metrics: {summary.get('evaluation_metric_summary', {})}",
        "",
        "Available artifacts",
        f"- Keyframes: {keyframes.get('status')} ({keyframes.get('keyframe_count', 0)} items)",
        (
            "- Annotated video: "
            f"{annotated_video.get('status')} "
            f"({annotated_video.get('annotated_video_reference') or '-'})"
        ),
        "",
        f"Disclaimer: {NOT_FOR_ENFORCEMENT_NOTE}",
    ]
    for reference in bundle.get("artifact_references", []):
        if isinstance(reference, dict):
            lines.append(
                f"- {reference.get('key')}: exists={reference.get('exists')} "
                f"path={reference.get('path') or '-'}"
            )
    return lines
