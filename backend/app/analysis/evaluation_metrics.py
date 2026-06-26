from collections.abc import Mapping
from typing import Any

from app.analysis.detection_metrics import compute_detection_benchmark
from app.analysis.tracking_metrics import compute_tracking_benchmark


def compute_event_metrics(
    expected_events: list[dict[str, Any]],
    actual_events: list[dict[str, Any]],
    *,
    frame_tolerance: int = 5,
) -> dict[str, Any]:
    if not expected_events:
        return {
            "status": "not_applicable",
            "reason": "missing expected events",
            "event_count_expected": 0,
            "event_count_actual": len(actual_events),
            "true_positive": 0,
            "false_positive": len(actual_events),
            "false_negative": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "failed_cases": [],
        }

    matched_actual: set[int] = set()
    matched_expected: set[int] = set()
    for expected_index, expected in enumerate(expected_events):
        for actual_index, actual in enumerate(actual_events):
            if actual_index in matched_actual:
                continue
            if _events_match(expected, actual, frame_tolerance=frame_tolerance):
                matched_expected.add(expected_index)
                matched_actual.add(actual_index)
                break

    true_positive = len(matched_expected)
    false_negative = len(expected_events) - true_positive
    false_positive = len(actual_events) - len(matched_actual)
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = (
        _round_metric((2 * precision * recall) / (precision + recall))
        if precision is not None and recall is not None and precision + recall > 0
        else None
    )
    failed_cases = [
        _event_failed_case("false_negative", expected=expected_events[index], actual={})
        for index in range(len(expected_events))
        if index not in matched_expected
    ]
    failed_cases.extend(
        _event_failed_case("false_positive", expected={}, actual=actual_events[index])
        for index in range(len(actual_events))
        if index not in matched_actual
    )

    return {
        "status": "available",
        "event_count_expected": len(expected_events),
        "event_count_actual": len(actual_events),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "failed_cases": failed_cases,
    }


def compute_flow_counting_metrics(
    expected_counts: dict[str, Any] | None,
    actual_counts: dict[str, Any] | None,
) -> dict[str, Any]:
    if not expected_counts:
        return {
            "status": "not_applicable",
            "reason": "missing expected flow counts",
            "expected_total": None,
            "actual_total": _extract_total_count(actual_counts or {}),
            "absolute_error": None,
            "mae": None,
            "mape": None,
            "by_class_error": {},
            "by_direction_error": {},
        }

    actual_counts = actual_counts or {}
    expected_total = _extract_total_count(expected_counts)
    actual_total = _extract_total_count(actual_counts)
    absolute_error = abs(expected_total - actual_total)
    expected_by_class = _extract_bucket_counts(expected_counts, "by_class", "class_name")
    actual_by_class = _extract_bucket_counts(actual_counts, "by_class", "class_name")
    expected_by_direction = _extract_bucket_counts(expected_counts, "by_direction", "direction")
    actual_by_direction = _extract_bucket_counts(actual_counts, "by_direction", "direction")

    return {
        "status": "available",
        "expected_total": expected_total,
        "actual_total": actual_total,
        "absolute_error": absolute_error,
        "mae": absolute_error,
        "mape": _safe_ratio(absolute_error, expected_total),
        "by_class_error": _bucket_abs_errors(expected_by_class, actual_by_class),
        "by_direction_error": _bucket_abs_errors(
            expected_by_direction,
            actual_by_direction,
        ),
    }


def compute_trajectory_metrics(trajectory_payload: dict[str, Any] | None) -> dict[str, Any]:
    points = _trajectory_points(trajectory_payload or {})
    if not points:
        return {
            "status": "empty",
            "track_count": 0,
            "total_trajectory_points": 0,
            "average_track_length": 0,
            "average_speed": None,
            "direction_available_count": 0,
        }

    track_ids = {point.get("track_id") for point in points if point.get("track_id") is not None}
    track_lengths = [
        float(point["track_length"])
        for point in points
        if _is_number(point.get("track_length"))
    ]
    speeds = [
        float(point["speed_px_per_second"])
        for point in points
        if _is_number(point.get("speed_px_per_second"))
    ]
    direction_available_count = sum(
        1 for point in points if point.get("moving_angle") is not None
    )
    return {
        "status": "available",
        "track_count": len(track_ids),
        "total_trajectory_points": len(points),
        "average_track_length": _mean(track_lengths),
        "average_speed": _mean(speeds) if speeds else None,
        "direction_available_count": direction_available_count,
    }


def compute_detection_metrics(
    annotation_payload: dict[str, Any] | None,
    detections: list[dict[str, Any]],
) -> dict[str, Any]:
    details = compute_detection_benchmark(
        predictions=detections,
        ground_truth=annotation_payload,
    )
    details["benchmark_definition"] = "VOC-style single-IoU AP; not COCO official mAP"
    return details


def compute_tracking_metrics(
    annotation_payload: dict[str, Any] | None,
    tracks: list[dict[str, Any]],
) -> dict[str, Any]:
    details = compute_tracking_benchmark(
        predictions=tracks,
        ground_truth=annotation_payload,
    )
    details["benchmark_definition"] = "Lightweight deterministic frame-level association; not TrackEval official"
    return details


def compute_bad_case_regression_metrics(
    bad_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    total_cases = len(bad_cases)
    status_counts: dict[str, int] = {}
    for bad_case in bad_cases:
        status = str(bad_case.get("status") or "open")
        status_counts[status] = status_counts.get(status, 0) + 1

    open_cases = status_counts.get("open", 0)
    fixed_cases = status_counts.get("fixed", 0)
    verified_cases = status_counts.get("verified", 0)
    ignored_cases = status_counts.get("wont_fix", 0) + status_counts.get("ignored", 0)
    denominator = max(fixed_cases + verified_cases + open_cases, 1)
    return {
        "status": "available" if total_cases else "empty",
        "total_cases": total_cases,
        "open_cases": open_cases,
        "fixed_cases": fixed_cases,
        "verified_cases": verified_cases,
        "ignored_cases": ignored_cases,
        "regression_pass_rate": _safe_ratio(verified_cases, denominator) or 0.0,
        "reopened_case_count": 0,
        "fixed_case_count": fixed_cases,
        "definition": "verified_cases / max(fixed_cases + verified_cases + open_cases, 1)",
        "rerun_based": False,
        "reason": "Artifact-backed MVP summary; no real rerun-based regression is executed.",
    }


def _events_match(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    frame_tolerance: int,
) -> bool:
    if str(expected.get("event_type")) != str(actual.get("event_type")):
        return False
    expected_start, expected_end = _event_frame_range(expected)
    actual_start, actual_end = _event_frame_range(actual)
    if expected_start is None or actual_start is None:
        return True
    return expected_start - frame_tolerance <= actual_end and actual_start <= expected_end + frame_tolerance


def _event_frame_range(event: Mapping[str, Any]) -> tuple[int | None, int | None]:
    start = _optional_int(event.get("start_frame") or event.get("frame_index"))
    end = _optional_int(event.get("end_frame") or event.get("frame_index"))
    if start is None and end is not None:
        start = end
    if end is None and start is not None:
        end = start
    return start, end


def _event_failed_case(
    failure_type: str,
    *,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> dict[str, Any]:
    event = expected or actual
    start, end = _event_frame_range(event)
    return {
        "failure_type": failure_type,
        "module": "event_engine",
        "expected": expected,
        "actual": actual,
        "frame_range": {"start_frame": start, "end_frame": end},
        "suggested_bad_case_type": failure_type,
    }


def _extract_total_count(payload: Mapping[str, Any]) -> int:
    summary = payload.get("summary")
    if isinstance(summary, Mapping):
        for key in ("total_count", "vehicle_count", "count"):
            if _is_number(summary.get(key)):
                return int(float(summary[key]))
    for key in ("total_count", "count"):
        if _is_number(payload.get(key)):
            return int(float(payload[key]))
    records = payload.get("records")
    if isinstance(records, list):
        return sum(int(float(record.get("count", record.get("total_count", 0)) or 0)) for record in records if isinstance(record, Mapping))
    return 0


def _extract_bucket_counts(
    payload: Mapping[str, Any],
    direct_key: str,
    record_key: str,
) -> dict[str, int]:
    direct = payload.get(direct_key)
    if isinstance(direct, Mapping):
        return {
            str(key): int(float(value or 0))
            for key, value in direct.items()
            if _is_number(value)
        }
    summary = payload.get("summary")
    if isinstance(summary, Mapping) and isinstance(summary.get(direct_key), Mapping):
        return {
            str(key): int(float(value or 0))
            for key, value in summary[direct_key].items()
            if _is_number(value)
        }
    counts: dict[str, int] = {}
    records = payload.get("records")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            bucket = record.get(record_key)
            if bucket is None:
                continue
            count = record.get("count", record.get("total_count", 0))
            if _is_number(count):
                counts[str(bucket)] = counts.get(str(bucket), 0) + int(float(count))
    return dict(sorted(counts.items()))


def _bucket_abs_errors(
    expected: Mapping[str, int],
    actual: Mapping[str, int],
) -> dict[str, int]:
    keys = sorted(set(expected) | set(actual))
    return {key: abs(int(expected.get(key, 0)) - int(actual.get(key, 0))) for key in keys}


def _trajectory_points(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    frames = payload.get("frames")
    if isinstance(frames, list):
        for frame in frames:
            if not isinstance(frame, Mapping):
                continue
            frame_points = frame.get("trajectory_points")
            if isinstance(frame_points, list):
                points.extend(point for point in frame_points if isinstance(point, dict))
    rows = payload.get("rows")
    if isinstance(rows, list):
        points.extend(row for row in rows if isinstance(row, dict))
    return points


def _mean(values: list[float]) -> int | float:
    value = sum(values) / len(values)
    return int(value) if value.is_integer() else _round_metric(value)


def _safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return _round_metric(float(numerator) / float(denominator))


def _round_metric(value: float) -> float:
    return round(value, 6)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
