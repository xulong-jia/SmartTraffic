from pathlib import Path
import json
from typing import Any

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.review_artifacts import (
    ReviewArtifactError,
    ReviewStateTransitionError,
    append_false_negative,
    apply_review_action,
    load_event_review_state,
    load_false_negatives,
    load_review_comments,
)
from app.core.config import get_settings


class ReviewService:
    """Stage 7B artifact-backed review state helper.

    This service intentionally does not expose Review API behavior yet. Stage 7C
    will translate these artifact operations into HTTP contracts.
    """

    def __init__(self, artifact_writer: TrafficArtifactWriter | None = None) -> None:
        self.artifact_writer = artifact_writer

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_7c_review_api"}

    def list_review_events(
        self,
        *,
        run_id: str,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        events = self._read_events(run_dir)
        review_state = load_event_review_state(run_dir, run_id=run_id)
        comments = load_review_comments(run_dir)
        alerts = self._read_alerts(run_dir)
        linked_alert_ids_by_event = _linked_alert_ids_by_event(alerts)
        comment_counts = _comment_counts_by_event(comments)

        items = [
            _build_review_event_item(
                run_id=run_id,
                event=event,
                state=review_state["events"].get(str(event.get("event_id"))),
                linked_alert_ids=linked_alert_ids_by_event.get(
                    str(event.get("event_id")),
                    [],
                ),
                comment_count=comment_counts.get(str(event.get("event_id")), 0),
            )
            for event in events
            if event.get("event_id") is not None
        ]
        filtered = [
            item
            for item in items
            if (status is None or item["review_status"] == status)
            and (event_type is None or item.get("event_type") == event_type)
        ]
        safe_offset = max(offset, 0)
        safe_limit = max(limit, 0)
        return {
            "items": filtered[safe_offset : safe_offset + safe_limit],
            "total": len(filtered),
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def get_review_event(self, *, run_id: str, event_id: str) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        event = self._get_event(run_dir, event_id)
        review_state = load_event_review_state(run_dir, run_id=run_id)
        comments = [
            comment
            for comment in load_review_comments(run_dir)
            if comment.get("event_id") == event_id
        ]
        linked_alerts = [
            alert for alert in self._read_alerts(run_dir) if alert.get("event_id") == event_id
        ]
        event_state = review_state["events"].get(event_id)
        enriched_event = _build_review_event_detail(
            run_id=run_id,
            event=event,
            state=event_state,
            linked_alert_ids=[str(alert.get("alert_id") or alert.get("id")) for alert in linked_alerts],
            comment_count=len(comments),
        )
        return {
            "run_id": run_id,
            "event": enriched_event,
            "review_state": event_state,
            "linked_alerts": linked_alerts,
            "comments": comments,
            "visual_artifacts": self._visual_artifacts(run_dir, event_id),
        }

    def list_review_comments(self, *, run_id: str) -> list[dict[str, Any]]:
        return load_review_comments(self._existing_run_dir(run_id))

    def query_review_comments(
        self,
        *,
        run_id: str,
        event_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        comments = self.list_review_comments(run_id=run_id)
        filtered = [
            comment
            for comment in comments
            if event_id is None or comment.get("event_id") == event_id
        ]
        safe_offset = max(offset, 0)
        safe_limit = max(limit, 0)
        return {
            "run_id": run_id,
            "event_id": event_id,
            "items": filtered[safe_offset : safe_offset + safe_limit],
            "total": len(filtered),
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def event_review_state(self, *, run_id: str) -> dict[str, Any]:
        return load_event_review_state(self._existing_run_dir(run_id), run_id=run_id)

    def apply_action(
        self,
        *,
        run_id: str,
        event_id: str,
        action: str,
        comment: str | None = None,
        reviewer: str | None = None,
        alert_id: str | None = None,
        source: str = "review_center",
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        self._ensure_event_or_review_state(run_dir, run_id=run_id, event_id=event_id)
        result = apply_review_action(
            run_dir,
            run_id=run_id,
            event_id=event_id,
            action=action,
            comment=comment,
            reviewer=reviewer,
            alert_id=alert_id,
            source=source,
        )
        comments = load_review_comments(run_dir)
        latest_review = _last_review_for_event(comments, event_id)
        state = load_event_review_state(run_dir, run_id=run_id)["events"][event_id]
        return {
            **result,
            "review": latest_review,
            "state": state,
        }

    def add_false_negative(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        false_negative = append_false_negative(
            run_dir,
            {
                **record,
                "run_id": run_id,
            },
        )
        comments = load_review_comments(run_dir)
        review = _last_review_for_event(comments, false_negative["false_negative_id"])
        state = load_event_review_state(run_dir, run_id=run_id)["events"][
            false_negative["false_negative_id"]
        ]
        return {
            "run_id": run_id,
            "status": "false_negative",
            "false_negative": false_negative,
            "review": review,
            "state": state,
        }

    def list_false_negatives(self, *, run_id: str) -> list[dict[str, Any]]:
        return load_false_negatives(self._existing_run_dir(run_id))

    def _run_dir(self, run_id: str) -> Path:
        return self._writer().base_dir / run_id

    def _existing_run_dir(self, run_id: str) -> Path:
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            raise KeyError(run_id)
        return run_dir

    def _read_events(self, run_dir: Path) -> list[dict[str, Any]]:
        events_path = run_dir / "events.jsonl"
        if not events_path.is_file():
            return []
        return _read_jsonl(events_path)

    def _read_alerts(self, run_dir: Path) -> list[dict[str, Any]]:
        alerts_path = run_dir / "alerts.jsonl"
        if not alerts_path.is_file():
            return []
        return _read_jsonl(alerts_path)

    def _get_event(self, run_dir: Path, event_id: str) -> dict[str, Any]:
        for event in self._read_events(run_dir):
            if event.get("event_id") == event_id:
                return event
        raise KeyError(event_id)

    def _ensure_event_or_review_state(
        self,
        run_dir: Path,
        *,
        run_id: str,
        event_id: str,
    ) -> None:
        if any(event.get("event_id") == event_id for event in self._read_events(run_dir)):
            return
        state = load_event_review_state(run_dir, run_id=run_id)
        if event_id in state["events"]:
            return
        raise KeyError(event_id)

    def _visual_artifacts(self, run_dir: Path, event_id: str) -> dict[str, Any]:
        keyframes_index_path = run_dir / "keyframes" / "index.json"
        keyframe_items: list[dict[str, Any]] = []
        keyframes_status = "missing"
        if keyframes_index_path.is_file():
            with keyframes_index_path.open(encoding="utf-8") as file:
                payload = json.load(file)
            keyframes_status = str(payload.get("status") or "available")
            items = payload.get("items")
            if isinstance(items, list):
                keyframe_items = [
                    item
                    for item in items
                    if isinstance(item, dict) and item.get("source_id") == event_id
                ]
        annotated_video_path = run_dir / "annotated_video.mp4"
        return {
            "keyframes": {
                "status": keyframes_status,
                "path": "keyframes/index.json",
                "items": keyframe_items,
            },
            "annotated_video": {
                "status": "available" if annotated_video_path.is_file() else "missing",
                "path": "annotated_video.mp4",
            },
        }

    def _writer(self) -> TrafficArtifactWriter:
        return self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _linked_alert_ids_by_event(alerts: list[dict[str, Any]]) -> dict[str, list[str]]:
    linked: dict[str, list[str]] = {}
    for alert in alerts:
        event_id = alert.get("event_id")
        alert_id = alert.get("alert_id") or alert.get("id")
        if event_id is None or alert_id is None:
            continue
        linked.setdefault(str(event_id), []).append(str(alert_id))
    return linked


def _comment_counts_by_event(comments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for comment in comments:
        event_id = comment.get("event_id")
        if event_id is None:
            continue
        counts[str(event_id)] = counts.get(str(event_id), 0) + 1
    return counts


def _build_review_event_item(
    *,
    run_id: str,
    event: dict[str, Any],
    state: dict[str, Any] | None,
    linked_alert_ids: list[str],
    comment_count: int,
) -> dict[str, Any]:
    original_status = str(event.get("status") or "pending")
    review_status = str(state.get("status") if state else original_status)
    return {
        "run_id": run_id,
        "event_id": str(event["event_id"]),
        "event_type": event.get("event_type"),
        "track_id": _optional_int(event.get("track_id")),
        "zone_id": event.get("zone_id"),
        "severity": event.get("severity"),
        "original_status": original_status,
        "review_status": review_status,
        "last_action": state.get("last_action") if state else None,
        "comment_count": int(state.get("comment_count") if state else comment_count),
        "linked_alert_ids": linked_alert_ids,
        "start_frame": _optional_int(event.get("start_frame")),
        "end_frame": _optional_int(event.get("end_frame")),
        "start_time_ms": _optional_int(event.get("start_time_ms")),
        "end_time_ms": _optional_int(event.get("end_time_ms")),
    }


def _build_review_event_detail(
    *,
    run_id: str,
    event: dict[str, Any],
    state: dict[str, Any] | None,
    linked_alert_ids: list[str],
    comment_count: int,
) -> dict[str, Any]:
    item = _build_review_event_item(
        run_id=run_id,
        event=event,
        state=state,
        linked_alert_ids=linked_alert_ids,
        comment_count=comment_count,
    )
    return {
        **event,
        **item,
    }


def _last_review_for_event(
    comments: list[dict[str, Any]],
    event_id: str,
) -> dict[str, Any]:
    for comment in reversed(comments):
        if comment.get("event_id") == event_id:
            return comment
    raise KeyError(event_id)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
