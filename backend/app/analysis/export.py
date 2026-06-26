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


def report_pdf_filename(run_id: str) -> str:
    return f"smarttraffic_report_{_safe_name(run_id)}.pdf"


def report_pdf(lines: Iterable[str]) -> bytes:
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_pdf_line(str(line)))
    if not wrapped_lines:
        wrapped_lines = [""]

    page_height = 792
    line_height = 14
    top_margin = 742
    bottom_margin = 54
    lines_per_page = max(1, (top_margin - bottom_margin) // line_height)
    pages = [
        wrapped_lines[index : index + lines_per_page]
        for index in range(0, len(wrapped_lines), lines_per_page)
    ]

    objects: list[bytes] = []
    font_object_number = 3 + len(pages) * 2
    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))

    for page_index, page_lines in enumerate(pages):
        page_object_number = 3 + page_index * 2
        content_object_number = page_object_number + 1
        page_object_numbers.append(page_object_number)
        content_object_numbers.append(content_object_number)
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
                f"/Contents {content_object_number} 0 R >>"
            ).encode("ascii")
        )
        content = _pdf_page_content(page_lines, top_margin=top_margin, line_height=line_height)
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_number, payload in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_number} 0 obj\n".encode("ascii"))
        output.extend(payload)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


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


def _wrap_pdf_line(line: str, width: int = 86) -> list[str]:
    safe_line = line.replace("\t", "    ")
    if not safe_line:
        return [""]
    words = safe_line.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [safe_line[:width]]


def _pdf_page_content(lines: list[str], *, top_margin: int, line_height: int) -> bytes:
    content = bytearray(b"BT\n/F1 10 Tf\n")
    y = top_margin
    for line in lines:
        content.extend(f"1 0 0 1 54 {y} Tm ({_pdf_escape(line)}) Tj\n".encode("latin-1"))
        y -= line_height
    content.extend(b"ET")
    return bytes(content)


def _pdf_escape(value: str) -> str:
    safe = value.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
