from __future__ import annotations

from collections.abc import Iterable, Mapping
import csv
import io
import json
import os
from pathlib import Path
from typing import Any


REPORT_EXPORT_SECTIONS = [
    "events",
    "alerts",
    "flow_counts",
    "zone_statistics",
    "bad_cases",
    "evaluation_results",
]

REPORT_EXPORT_HEADERS: dict[str, list[str]] = {
    "events": [
        "event_id",
        "run_id",
        "event_type",
        "status",
        "severity",
        "track_id",
        "zone_id",
        "frame_index",
        "timestamp_ms",
    ],
    "alerts": [
        "alert_id",
        "run_id",
        "event_id",
        "alert_type",
        "level",
        "status",
        "message",
        "created_at",
    ],
    "flow_counts": [
        "id",
        "run_id",
        "line_id",
        "class_name",
        "direction",
        "count",
        "window_start_ms",
        "window_end_ms",
    ],
    "zone_statistics": [
        "id",
        "run_id",
        "zone_id",
        "metric_name",
        "metric_value",
        "window_start_ms",
        "window_end_ms",
    ],
    "bad_cases": [
        "case_id",
        "run_id",
        "event_id",
        "case_type",
        "module",
        "status",
        "description",
        "source",
        "created_at",
    ],
    "evaluation_results": [
        "evaluation_result_id",
        "evaluation_run_id",
        "run_id",
        "dataset_id",
        "evaluation_type",
        "metric_name",
        "metric_value",
        "status",
        "created_at",
    ],
}


def export_summary_placeholder() -> dict[str, str]:
    return {"status": "implemented", "stage": "full_stage_6ab_report_export"}


def report_csv(section: str, rows: Iterable[Mapping[str, Any]]) -> str:
    headers = REPORT_EXPORT_HEADERS[section]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_value(row.get(key)) for key in headers})
    return buffer.getvalue()


def report_filename(run_id: str, section: str, extension: str) -> str:
    safe_run_id = _safe_name(run_id)
    safe_section = _safe_name(section)
    return f"smarttraffic_{safe_run_id}_{safe_section}.{extension}"


def sanitize_report_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_report_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_report_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_report_payload(item) for item in value]
    if isinstance(value, Path):
        return sanitize_report_path(str(value))
    if isinstance(value, str):
        return sanitize_report_path(value)
    return value


def sanitize_report_path(value: str) -> str:
    if not value:
        return value
    if os.path.isabs(value):
        return Path(value).name
    return value


def _csv_value(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    return json.dumps(sanitize_report_payload(value), ensure_ascii=False, sort_keys=True)


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
