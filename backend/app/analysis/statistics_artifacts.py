from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


FLOW_COUNTS_SCHEMA_VERSION = "stage6.flow_counts.v1"
ZONE_STATISTICS_SCHEMA_VERSION = "stage6.zone_statistics.v1"
DEFAULT_WINDOW_MS = 60_000

VEHICLE_CLASSES = {"bicycle", "bus", "car", "motorcycle", "truck"}


def build_flow_counts_artifact(
    *,
    run_id: str,
    run_dir: Path,
    metadata: dict[str, Any],
    window_ms: int = DEFAULT_WINDOW_MS,
) -> dict[str, Any]:
    events = _read_jsonl(_artifact_path(run_dir, metadata, "events_jsonl", "events.jsonl"))
    evidence_rows = _read_jsonl(
        _artifact_path(run_dir, metadata, "event_evidence_jsonl", "event_evidence.jsonl")
    )
    line_evidence_by_event_id = _evidence_by_event_id(
        evidence_rows,
        evidence_type="line_crossing",
    )

    records: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for event in events:
        if event.get("event_type") != "flow_counting":
            continue
        event_id = _string_or_none(event.get("event_id"))
        if event_id is None or event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)

        evidence = line_evidence_by_event_id.get(event_id, {})
        evidence_json = _mapping(evidence.get("evidence_json")) or _mapping(
            event.get("evidence")
        )
        timestamp_ms = _first_int(
            event.get("end_time_ms"),
            evidence.get("timestamp_ms"),
            evidence_json.get("timestamp_ms"),
            event.get("start_time_ms"),
            default=0,
        )
        frame_index = _first_int(
            event.get("end_frame"),
            evidence.get("frame_index"),
            evidence_json.get("frame_index"),
            event.get("start_frame"),
            default=0,
        )
        class_name = _first_string(
            event.get("class_name"),
            evidence_json.get("class_name"),
            default="unknown",
        )
        zone_id = _first_string(
            event.get("zone_id"),
            evidence.get("zone_id"),
            evidence_json.get("zone_id"),
            default="unknown",
        )
        line_id = _first_string(
            evidence_json.get("line_id"),
            evidence_json.get("line_name"),
            evidence_json.get("id"),
            event.get("rule_id"),
            default="unknown",
        )
        direction = _flow_direction(
            _first_string(
                evidence_json.get("crossing_direction"),
                evidence_json.get("direction"),
                default="unknown",
            )
        )
        track_id = _first_int(
            event.get("track_id"),
            evidence.get("track_id"),
            evidence_json.get("track_id"),
            default=None,
        )

        records.append(
            {
                "event_id": event_id,
                "track_id": track_id,
                "class_name": class_name,
                "zone_id": zone_id,
                "counting_line_id": line_id,
                "direction": direction,
                "frame_index": frame_index,
                "timestamp_ms": timestamp_ms,
            }
        )

    windows = _flow_windows(records, window_ms=window_ms)
    return {
        "schema_version": FLOW_COUNTS_SCHEMA_VERSION,
        "run_id": run_id,
        "video_id": str(metadata.get("video_id", "")),
        "generated_at": _utc_now_iso(),
        "window_ms": window_ms,
        "source_artifacts": {
            "events": _artifact_name(metadata, "events_jsonl", "events.jsonl"),
            "event_evidence": _artifact_name(
                metadata,
                "event_evidence_jsonl",
                "event_evidence.jsonl",
            ),
            "rule_executions": _artifact_name(
                metadata,
                "rule_executions_jsonl",
                "rule_executions.jsonl",
            ),
        },
        "summary": _flow_summary(records),
        "windows": windows,
        "records": records,
    }


def build_zone_statistics_artifact(
    *,
    run_id: str,
    run_dir: Path,
    metadata: dict[str, Any],
    window_ms: int = DEFAULT_WINDOW_MS,
) -> dict[str, Any]:
    trajectory_frames = _read_jsonl(
        _artifact_path(
            run_dir,
            metadata,
            "trajectory_points_jsonl",
            "trajectory_points.jsonl",
        )
    )
    events = _read_jsonl(_artifact_path(run_dir, metadata, "events_jsonl", "events.jsonl"))
    evidence_rows = _read_jsonl(
        _artifact_path(run_dir, metadata, "event_evidence_jsonl", "event_evidence.jsonl")
    )
    zone_evidence_by_event_id = _evidence_by_event_id(
        evidence_rows,
        evidence_type="zone_statistics",
    )

    windows = _zone_windows(trajectory_frames, window_ms=window_ms)
    congestion_events = _congestion_events(events, zone_evidence_by_event_id)
    return {
        "schema_version": ZONE_STATISTICS_SCHEMA_VERSION,
        "run_id": run_id,
        "video_id": str(metadata.get("video_id", "")),
        "generated_at": _utc_now_iso(),
        "window_ms": window_ms,
        "source_artifacts": {
            "trajectory_points": _artifact_name(
                metadata,
                "trajectory_points_jsonl",
                "trajectory_points.jsonl",
            ),
            "events": _artifact_name(metadata, "events_jsonl", "events.jsonl"),
            "event_evidence": _artifact_name(
                metadata,
                "event_evidence_jsonl",
                "event_evidence.jsonl",
            ),
        },
        "summary": _zone_summary(windows, congestion_events),
        "windows": windows,
        "congestion_events": congestion_events,
    }


def _flow_windows(
    records: list[dict[str, Any]],
    *,
    window_ms: int,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[int, int, str, str, str, str], dict[str, Any]] = {}
    for record in records:
        timestamp_ms = int(record["timestamp_ms"])
        start_ms = _window_start(timestamp_ms, window_ms)
        key = (
            start_ms,
            start_ms + window_ms,
            str(record["zone_id"]),
            str(record["counting_line_id"]),
            str(record["class_name"]),
            str(record["direction"]),
        )
        bucket = buckets.setdefault(
            key,
            {
                "time_window_start_ms": start_ms,
                "time_window_end_ms": start_ms + window_ms,
                "zone_id": str(record["zone_id"]),
                "counting_line_id": str(record["counting_line_id"]),
                "class_name": str(record["class_name"]),
                "direction": str(record["direction"]),
                "in_count": 0,
                "out_count": 0,
                "unknown_direction_count": 0,
                "total_count": 0,
                "track_ids": set(),
                "event_ids": set(),
            },
        )
        direction = str(record["direction"])
        if direction == "in":
            bucket["in_count"] += 1
        elif direction == "out":
            bucket["out_count"] += 1
        else:
            bucket["unknown_direction_count"] += 1
        bucket["total_count"] += 1
        if record.get("track_id") is not None:
            bucket["track_ids"].add(record["track_id"])
        bucket["event_ids"].add(str(record["event_id"]))

    return [
        {
            **{key: value for key, value in bucket.items() if key not in {"track_ids", "event_ids"}},
            "track_ids": _sorted_values(bucket["track_ids"]),
            "event_ids": sorted(bucket["event_ids"]),
        }
        for _, bucket in sorted(buckets.items())
    ]


def _flow_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_class = Counter(str(record["class_name"]) for record in records)
    by_zone = Counter(str(record["zone_id"]) for record in records)
    by_line = Counter(str(record["counting_line_id"]) for record in records)
    by_direction = Counter(str(record["direction"]) for record in records)
    return {
        "total_count": len(records),
        "vehicle_count": sum(
            1 for record in records if str(record["class_name"]) in VEHICLE_CLASSES
        ),
        "person_count": sum(
            1 for record in records if str(record["class_name"]) == "person"
        ),
        "by_class": dict(sorted(by_class.items())),
        "by_zone": dict(sorted(by_zone.items())),
        "by_line": dict(sorted(by_line.items())),
        "by_direction": dict(sorted(by_direction.items())),
    }


def _zone_windows(
    trajectory_frames: list[dict[str, Any]],
    *,
    window_ms: int,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[int, int, str], dict[str, Any]] = {}
    for frame in trajectory_frames:
        timestamp_ms = _first_int(frame.get("timestamp_ms"), default=0) or 0
        frame_start = _window_start(timestamp_ms, window_ms)
        for point in frame.get("trajectory_points", []) or []:
            if not isinstance(point, dict):
                continue
            zone_ids = _zone_ids(point)
            if not zone_ids:
                continue
            class_name = _first_string(point.get("class_name"), default="unknown")
            track_id = _first_int(point.get("track_id"), default=None)
            speed = _first_float(point.get("speed_px_per_frame"), default=None)
            for zone_id in zone_ids:
                key = (frame_start, frame_start + window_ms, zone_id)
                bucket = buckets.setdefault(
                    key,
                    {
                        "time_window_start_ms": frame_start,
                        "time_window_end_ms": frame_start + window_ms,
                        "zone_id": zone_id,
                        "vehicle_track_ids": set(),
                        "person_track_ids": set(),
                        "all_track_ids": set(),
                        "anonymous_vehicle_count": 0,
                        "anonymous_person_count": 0,
                        "anonymous_occupancy_count": 0,
                        "speeds": [],
                        "class_counts": Counter(),
                    },
                )
                bucket["class_counts"][class_name] += 1
                if speed is not None:
                    bucket["speeds"].append(speed)
                if track_id is not None:
                    bucket["all_track_ids"].add(track_id)
                    if class_name in VEHICLE_CLASSES:
                        bucket["vehicle_track_ids"].add(track_id)
                    elif class_name == "person":
                        bucket["person_track_ids"].add(track_id)
                else:
                    bucket["anonymous_occupancy_count"] += 1
                    if class_name in VEHICLE_CLASSES:
                        bucket["anonymous_vehicle_count"] += 1
                    elif class_name == "person":
                        bucket["anonymous_person_count"] += 1

    rows: list[dict[str, Any]] = []
    for _, bucket in sorted(buckets.items()):
        vehicle_count = (
            len(bucket["vehicle_track_ids"]) + bucket["anonymous_vehicle_count"]
        )
        person_count = len(bucket["person_track_ids"]) + bucket["anonymous_person_count"]
        occupancy_count = len(bucket["all_track_ids"]) + bucket["anonymous_occupancy_count"]
        speeds = bucket["speeds"]
        rows.append(
            {
                "time_window_start_ms": bucket["time_window_start_ms"],
                "time_window_end_ms": bucket["time_window_end_ms"],
                "zone_id": bucket["zone_id"],
                "vehicle_count": vehicle_count,
                "person_count": person_count,
                "occupancy_count": occupancy_count,
                "avg_speed_px_per_frame": (
                    round(sum(speeds) / len(speeds), 6) if speeds else None
                ),
                "class_counts": dict(sorted(bucket["class_counts"].items())),
                "track_ids": _sorted_values(bucket["all_track_ids"]),
            }
        )
    return rows


def _congestion_events(
    events: list[dict[str, Any]],
    evidence_by_event_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for event in events:
        if event.get("event_type") != "congestion":
            continue
        event_id = _string_or_none(event.get("event_id"))
        if event_id is None or event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)

        evidence = evidence_by_event_id.get(event_id, {})
        evidence_json = _mapping(evidence.get("evidence_json")) or _mapping(
            event.get("evidence")
        )
        rows.append(
            {
                "event_id": event_id,
                "zone_id": _first_string(
                    evidence_json.get("zone_id"),
                    evidence.get("zone_id"),
                    event.get("zone_id"),
                    default="unknown",
                ),
                "frame_index": _first_int(
                    evidence.get("frame_index"),
                    evidence_json.get("frame_index"),
                    event.get("end_frame"),
                    default=0,
                ),
                "timestamp_ms": _first_int(
                    evidence.get("timestamp_ms"),
                    evidence_json.get("timestamp_ms"),
                    event.get("end_time_ms"),
                    default=0,
                ),
                "vehicle_count": _first_int(
                    evidence_json.get("vehicle_count"),
                    default=0,
                ),
                "avg_speed_px_per_frame": _first_float(
                    evidence_json.get("avg_speed_px_per_frame"),
                    default=None,
                ),
                "track_ids": _sorted_values(
                    _sequence_values(evidence_json.get("track_ids"))
                ),
                "class_counts": dict(
                    sorted(_mapping(evidence_json.get("class_counts")).items())
                ),
            }
        )
    return rows


def _zone_summary(
    windows: list[dict[str, Any]],
    congestion_events: list[dict[str, Any]],
) -> dict[str, Any]:
    zone_ids = {
        str(item["zone_id"])
        for item in [*windows, *congestion_events]
        if item.get("zone_id") is not None
    }
    avg_speeds = [
        item["avg_speed_px_per_frame"]
        for item in [*windows, *congestion_events]
        if item.get("avg_speed_px_per_frame") is not None
    ]
    return {
        "zone_count": len(zone_ids),
        "total_windows": len(windows),
        "vehicle_count": sum(int(item.get("vehicle_count") or 0) for item in windows),
        "person_count": sum(int(item.get("person_count") or 0) for item in windows),
        "max_vehicle_count": max(
            [0]
            + [int(item.get("vehicle_count") or 0) for item in windows]
            + [int(item.get("vehicle_count") or 0) for item in congestion_events]
        ),
        "min_avg_speed_px_per_frame": min(avg_speeds) if avg_speeds else None,
        "congestion_event_count": len(congestion_events),
    }


def _evidence_by_event_id(
    evidence_rows: list[dict[str, Any]],
    *,
    evidence_type: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        if row.get("evidence_type") != evidence_type:
            continue
        event_id = _string_or_none(row.get("event_id"))
        if event_id is None or event_id in indexed:
            continue
        indexed[event_id] = row
    return indexed


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _artifact_path(
    run_dir: Path,
    metadata: dict[str, Any],
    key: str,
    default: str,
) -> Path:
    return run_dir / _artifact_name(metadata, key, default)


def _artifact_name(metadata: dict[str, Any], key: str, default: str) -> str:
    artifacts = metadata.get("artifacts")
    if isinstance(artifacts, dict):
        value = artifacts.get(key)
        if value:
            return str(value)
    return default


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _sequence_values(value: Any) -> list[Any]:
    if isinstance(value, list | tuple | set):
        return list(value)
    return []


def _zone_ids(point: dict[str, Any]) -> list[str]:
    zone_ids = []
    raw_zone_ids = point.get("zone_ids")
    if isinstance(raw_zone_ids, list | tuple | set):
        zone_ids.extend(str(zone_id) for zone_id in raw_zone_ids if zone_id)
    elif raw_zone_ids:
        zone_ids.append(str(raw_zone_ids))

    raw_zone_id = point.get("zone_id")
    if raw_zone_id:
        zone_ids.append(str(raw_zone_id))

    zone_history = point.get("zone_history")
    if isinstance(zone_history, list | tuple):
        for item in zone_history:
            if isinstance(item, dict) and item.get("zone_id"):
                zone_ids.append(str(item["zone_id"]))
            elif item:
                zone_ids.append(str(item))

    return sorted(set(zone_ids))


def _flow_direction(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"positive", "in", "entry", "enter"}:
        return "in"
    if normalized in {"negative", "out", "exit", "leave"}:
        return "out"
    return "unknown"


def _window_start(timestamp_ms: int, window_ms: int) -> int:
    if window_ms <= 0:
        return 0
    return (timestamp_ms // window_ms) * window_ms


def _first_string(*values: Any, default: str) -> str:
    for value in values:
        if value is not None and value != "":
            return str(value)
    return default


def _first_int(*values: Any, default: int | None) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _first_float(*values: Any, default: float | None) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _string_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _sorted_values(values: Any) -> list[Any]:
    return sorted(list(values), key=lambda value: (str(type(value)), str(value)))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
