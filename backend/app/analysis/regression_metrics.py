from collections import Counter
from collections.abc import Mapping
from typing import Any

from app.events.engine import EventEngine


IGNORED_STATUSES = {"ignored", "wont_fix"}
REOPENABLE_STATUSES = {"fixed", "verified"}
FIXABLE_STATUSES = {"open", "triaged"}


def compute_bad_case_regression(
    bad_cases: list[dict[str, Any]],
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    config = dict(config or {})
    filtered_cases = _filter_cases(bad_cases, config)
    case_results = [_evaluate_case(record) for record in filtered_cases]
    status_counts = Counter(str(record.get("status") or "open") for record in filtered_cases)
    passed_count = sum(1 for result in case_results if result["passed"] is True)
    failed_count = sum(1 for result in case_results if result["passed"] is False)
    ignored_count = sum(1 for result in case_results if result["ignored"])
    insufficient_count = sum(1 for result in case_results if result["reason"] == "insufficient_data")
    evaluated_count = passed_count + failed_count
    fixed_count = sum(1 for result in case_results if result["fixed"])
    reopened_count = sum(1 for result in case_results if result["reopened"])
    pass_rate = _ratio_or_zero(passed_count, evaluated_count)
    return {
        "status": "available" if evaluated_count else ("empty" if not filtered_cases else "insufficient_data"),
        "evaluation_mode": "deterministic_replay",
        "apply_updates": bool(config.get("apply_updates", False)),
        "filters": _active_filters(config),
        "total_case_count": len(filtered_cases),
        "evaluated_case_count": evaluated_count,
        "passed_case_count": passed_count,
        "failed_case_count": failed_count,
        "fixed_case_count": fixed_count,
        "reopened_case_count": reopened_count,
        "ignored_case_count": ignored_count,
        "insufficient_data_count": insufficient_count,
        "updated_case_count": 0,
        "regression_pass_rate": pass_rate,
        "by_case_type": _group_counts(case_results, "case_type"),
        "by_module": _group_counts(case_results, "module"),
        "case_results": case_results,
        # Backward-compatible summary keys used by existing Evaluation Center UI/tests.
        "total_cases": len(filtered_cases),
        "open_cases": status_counts.get("open", 0),
        "fixed_cases": status_counts.get("fixed", 0),
        "verified_cases": status_counts.get("verified", 0),
        "ignored_cases": status_counts.get("ignored", 0) + status_counts.get("wont_fix", 0),
        "reopened_case_count": reopened_count,
        "definition": "passed_case_count / max(passed_case_count + failed_case_count, 1)",
        "rerun_based": True,
        "reason": "deterministic replay; full video pipeline rerun is not executed",
    }


def regression_failed_cases(details: Mapping[str, Any]) -> list[dict[str, Any]]:
    failed_cases: list[dict[str, Any]] = []
    for result in details.get("case_results", []):
        if not isinstance(result, Mapping) or result.get("passed") is not False:
            continue
        frame_index = _optional_int(result.get("frame_index"))
        failed_cases.append(
            {
                "failure_type": "regression_failed",
                "module": str(result.get("module") or "bad_case_regression"),
                "expected": {
                    "bad_case_id": result.get("bad_case_id"),
                    "expected_result": result.get("expected_result"),
                },
                "actual": {
                    "actual_result": result.get("actual_result"),
                    "replay_result": result.get("replay_result"),
                    "reason": result.get("reason"),
                },
                "frame_range": {"start_frame": frame_index, "end_frame": frame_index},
                "suggested_bad_case_type": str(result.get("case_type") or "other"),
            }
        )
    return failed_cases


def _evaluate_case(record: Mapping[str, Any]) -> dict[str, Any]:
    previous_status = str(record.get("status") or "open")
    base = {
        "bad_case_id": str(record.get("case_id") or record.get("id") or ""),
        "case_type": str(record.get("case_type") or record.get("type") or "other"),
        "module": str(record.get("module") or "other"),
        "previous_status": previous_status,
        "expected_result": str(record.get("expected_result") or ""),
        "actual_result": str(record.get("actual_result") or ""),
        "frame_index": record.get("frame_index"),
        "replay_result": None,
        "passed": None,
        "evaluated": False,
        "ignored": False,
        "fixed": False,
        "reopened": False,
        "reason": "insufficient_data",
        "suggested_status": previous_status,
    }
    if previous_status in IGNORED_STATUSES:
        return {**base, "ignored": True, "reason": "ignored_status"}

    replay = _run_replay(record)
    if replay["status"] == "insufficient_data":
        return {**base, "replay_result": replay.get("replay_result"), "reason": "insufficient_data"}

    passed = bool(replay["passed"])
    fixed = passed and previous_status in FIXABLE_STATUSES
    reopened = (not passed) and previous_status in REOPENABLE_STATUSES
    suggested_status = "fixed" if fixed else "open" if reopened else previous_status
    return {
        **base,
        "replay_result": replay["replay_result"],
        "passed": passed,
        "evaluated": True,
        "fixed": fixed,
        "reopened": reopened,
        "reason": replay["reason"],
        "suggested_status": suggested_status,
    }


def _run_replay(record: Mapping[str, Any]) -> dict[str, Any]:
    rule_replay = record.get("rule_replay")
    if isinstance(rule_replay, Mapping):
        return _run_rule_replay(rule_replay)
    regression_replay = record.get("regression_replay")
    if isinstance(regression_replay, Mapping):
        return _run_status_replay(record, regression_replay)
    return {"status": "insufficient_data", "replay_result": None}


def _run_status_replay(
    record: Mapping[str, Any],
    replay: Mapping[str, Any],
) -> dict[str, Any]:
    replay_result = {
        "mode": "status_replay",
        "actual_result": replay.get("actual_result", replay.get("result")),
    }
    if "passed" in replay:
        passed = bool(replay["passed"])
        return {
            "status": "available",
            "passed": passed,
            "reason": "status_replay_passed" if passed else "status_replay_failed",
            "replay_result": replay_result,
        }
    expected_result = str(replay.get("expected_result", record.get("expected_result") or ""))
    actual_result = replay_result["actual_result"]
    if expected_result == "" or actual_result is None:
        return {"status": "insufficient_data", "replay_result": replay_result}
    passed = _normalize_result(expected_result) == _normalize_result(str(actual_result))
    return {
        "status": "available",
        "passed": passed,
        "reason": "status_replay_passed" if passed else "status_replay_failed",
        "replay_result": replay_result,
    }


def _run_rule_replay(replay: Mapping[str, Any]) -> dict[str, Any]:
    rules = replay.get("rules")
    frames = replay.get("trajectory_frames", replay.get("frames"))
    if not isinstance(rules, list) or not isinstance(frames, list):
        return {"status": "insufficient_data", "replay_result": {"mode": "rule_replay"}}
    expected_event_count = _optional_int(replay.get("expected_event_count"))
    if expected_event_count is None:
        return {"status": "insufficient_data", "replay_result": {"mode": "rule_replay"}}
    event_type = replay.get("event_type")
    engine = EventEngine(
        run_id=str(replay.get("run_id") or "regression_replay"),
        video_id=str(replay.get("video_id") or "regression_replay"),
    )
    output = engine.evaluate(frames, rules=rules, zones=replay.get("zones") if isinstance(replay.get("zones"), list) else [])
    events = output.get("events", [])
    if event_type is not None:
        events = [event for event in events if event.get("event_type") == event_type]
    event_count = len(events)
    passed = event_count == expected_event_count
    return {
        "status": "available",
        "passed": passed,
        "reason": "rule_replay_passed" if passed else "rule_replay_failed",
        "replay_result": {
            "mode": "rule_replay",
            "event_type": event_type,
            "event_count": event_count,
            "expected_event_count": expected_event_count,
            "rule_execution_count": len(output.get("rule_executions", [])),
        },
    }


def _filter_cases(
    bad_cases: list[dict[str, Any]],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    tags = config.get("tags")
    if tags is None and config.get("tag") is not None:
        tags = [config["tag"]]
    required_tags = {str(tag) for tag in tags} if isinstance(tags, list) else set()
    dataset_id = config.get("dataset_id")
    return [
        record
        for record in bad_cases
        if (config.get("case_type") is None or record.get("case_type") == config.get("case_type") or record.get("type") == config.get("case_type"))
        and (config.get("module") is None or record.get("module") == config.get("module"))
        and (config.get("status") is None or record.get("status") == config.get("status"))
        and (not required_tags or required_tags.issubset({str(tag) for tag in record.get("tags", [])}))
        and (dataset_id is None or record.get("dataset_id") == dataset_id or record.get("evaluation_dataset_id") == dataset_id)
    ]


def _active_filters(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: config[key]
        for key in ("case_type", "module", "status", "tag", "tags", "dataset_id")
        if config.get(key) is not None
    }


def _group_counts(case_results: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {}
    for result in case_results:
        group = groups.setdefault(
            str(result.get(key) or "unknown"),
            {"total": 0, "passed": 0, "failed": 0, "ignored": 0, "insufficient_data": 0},
        )
        group["total"] += 1
        if result["passed"] is True:
            group["passed"] += 1
        elif result["passed"] is False:
            group["failed"] += 1
        elif result["ignored"]:
            group["ignored"] += 1
        else:
            group["insufficient_data"] += 1
    return dict(sorted(groups.items()))


def _normalize_result(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _ratio_or_zero(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
