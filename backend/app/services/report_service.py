from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.analysis.export import (
    REPORT_EXPORT_HEADERS,
    REPORT_EXPORT_SECTIONS,
    report_csv,
    sanitize_report_payload,
)
from app.services.alert_service import AlertService
from app.services.bad_case_service import BadCaseService
from app.services.evaluation_service import EvaluationService
from app.services.event_lifecycle_service import EventLifecycleService
from app.services.traffic_analysis_service import traffic_analysis_service
from app.repositories import TrafficAnalysisRunRepository


NOT_FOR_ENFORCEMENT_NOTE = (
    "SmartTraffic reports are for analysis and review only; not for traffic enforcement."
)


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
