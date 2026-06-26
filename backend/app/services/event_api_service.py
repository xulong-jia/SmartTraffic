from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.analysis.artifact_compatibility import discover_run_artifacts
from app.core.config import get_settings
from app.repositories import (
    BadCaseRepository,
    EventEvidenceRepository,
    EventRepository,
    TrafficAnalysisRunRepository,
)


VALID_EVENT_STATUSES = {
    "pending",
    "confirmed",
    "false_positive",
    "false_negative",
    "ignored",
    "resolved",
}


class EventApiService:
    def __init__(self, session: Session) -> None:
        self.events = EventRepository(session)
        self.evidence = EventEvidenceRepository(session)
        self.runs = TrafficAnalysisRunRepository(session)
        self.bad_cases = BadCaseRepository(session)

    def list_events(
        self,
        *,
        run_id: str | None = None,
        video_id: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        track_id: str | None = None,
    ) -> dict[str, Any]:
        rows = self.events.list(run_id=run_id, video_id=video_id, type=event_type)
        db_items = [_event_from_model(row) for row in rows]
        items = list(db_items)
        items = _filter_events(
            items,
            status=status,
            severity=severity,
            track_id=track_id,
        )
        if db_items:
            return {"source": "db", "items": items, "total": len(items)}
        if run_id is None:
            return {"source": "db", "items": [], "total": 0}
        artifact_items = self._artifact_events(run_id)
        artifact_items = _filter_events(
            artifact_items,
            video_id=video_id,
            event_type=event_type,
            status=status,
            severity=severity,
            track_id=track_id,
        )
        return {
            "source": "artifact" if artifact_items else "empty",
            "items": artifact_items,
            "total": len(artifact_items),
        }

    def get_event(self, event_id: str, *, run_id: str | None = None) -> dict[str, Any]:
        row = self.events.get(event_id)
        if row is not None:
            item = _event_from_model(row)
            item["event_evidence"] = [
                _evidence_from_model(evidence)
                for evidence in self.evidence.list(event_id=event_id)
            ]
            return item
        artifact = self._find_artifact_event(event_id, run_id=run_id)
        if artifact is None:
            raise KeyError(event_id)
        artifact["event_evidence"] = []
        return artifact

    def update_status(
        self,
        event_id: str,
        status: str,
        *,
        actor: str | None = None,
    ) -> dict[str, Any]:
        if status not in VALID_EVENT_STATUSES:
            raise ValueError(f"unsupported event status: {status}")
        existing = self.events.get(event_id)
        if existing is None:
            raise KeyError(event_id)
        payload = dict(existing.payload or {})
        if actor:
            payload["audit"] = {
                **dict(payload.get("audit") or {}),
                "last_actor": actor,
                "last_action": "event.status_update",
            }
        row = self.events.update(event_id, status=status, payload=payload)
        if row is None:
            raise KeyError(event_id)
        return _event_from_model(row)

    def create_bad_case(
        self,
        event_id: str,
        payload: dict[str, Any],
        *,
        actor: str | None = None,
    ) -> dict[str, Any]:
        event = self.events.get(event_id)
        if event is None:
            raise KeyError(event_id)
        case_id = str(payload.get("id") or f"bad_{uuid4().hex[:12]}")
        bad_case = self.bad_cases.create(
            id=case_id,
            run_id=event.run_id,
            event_id=event.id,
            type=str(payload.get("case_type") or "other"),
            status=str(payload.get("status") or "open"),
            severity=event.severity,
            description=payload.get("description"),
            tags=_with_actor_tag(list(payload.get("tags") or []), actor),
            payload={
                "video_id": event.video_id,
                "track_id": event.track_id,
                "module": payload.get("module") or "event_engine",
                "expected_result": payload.get("expected_result") or "",
                "actual_result": payload.get("actual_result") or "",
                "source": "event_api",
                "audit_actor": actor,
            },
        )
        return _bad_case_from_model(bad_case)

    def _find_artifact_event(
        self,
        event_id: str,
        *,
        run_id: str | None,
    ) -> dict[str, Any] | None:
        run_ids = [run_id] if run_id is not None else self._candidate_artifact_run_ids()
        for candidate_run_id in run_ids:
            if candidate_run_id is None:
                continue
            for item in self._artifact_events(candidate_run_id):
                if item["id"] == event_id:
                    return item
        return None

    def _candidate_artifact_run_ids(self) -> list[str]:
        base_dir = get_settings().results_dir
        if not base_dir.is_dir():
            return []
        return sorted(path.name for path in base_dir.iterdir() if path.is_dir())

    def _artifact_events(self, run_id: str) -> list[dict[str, Any]]:
        import json

        discovery = discover_run_artifacts(run_id, result_dir=self._result_dir(run_id))
        events_path = discovery.paths["events_jsonl"].path
        if not events_path.is_file():
            return []
        items = []
        with events_path.open(encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    items.append(_event_from_artifact(json.loads(stripped), run_id=run_id))
        return items

    def _result_dir(self, run_id: str) -> Path:
        run = self.runs.get(run_id)
        if run is not None and run.result_dir:
            return Path(run.result_dir)
        return get_settings().results_dir / run_id


def _filter_events(
    items: list[dict[str, Any]],
    *,
    video_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    track_id: str | None = None,
) -> list[dict[str, Any]]:
    filtered = []
    for item in items:
        if video_id is not None and item.get("video_id") != video_id:
            continue
        if event_type is not None and item.get("event_type") != event_type:
            continue
        if status is not None and item.get("status") != status:
            continue
        if severity is not None and item.get("severity") != severity:
            continue
        if track_id is not None and str(item.get("track_id")) != str(track_id):
            continue
        filtered.append(item)
    return filtered


def _event_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    return {
        "id": row.id,
        "event_id": row.id,
        "run_id": row.run_id,
        "video_id": row.video_id,
        "rule_id": row.rule_id,
        "zone_id": row.zone_id,
        "event_type": row.type,
        "type": row.type,
        "status": row.status,
        "severity": row.severity,
        "frame_index": row.frame_index,
        "timestamp_ms": row.timestamp_ms,
        "track_id": row.track_id,
        "payload": payload,
        "source": "db",
    }


def _evidence_from_model(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "run_id": row.run_id,
        "evidence_type": row.evidence_type,
        "payload": row.payload or {},
        "artifact_path": row.artifact_path,
        "source": "db",
    }


def _event_from_artifact(row: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    event_id = str(row.get("event_id") or row.get("id"))
    return {
        "id": event_id,
        "event_id": event_id,
        "run_id": str(row.get("run_id") or run_id),
        "video_id": row.get("video_id"),
        "rule_id": row.get("rule_id"),
        "zone_id": row.get("zone_id"),
        "event_type": row.get("event_type") or row.get("type"),
        "type": row.get("event_type") or row.get("type"),
        "status": row.get("status") or "pending",
        "severity": row.get("severity"),
        "frame_index": row.get("frame_index") or row.get("start_frame"),
        "timestamp_ms": row.get("timestamp_ms") or row.get("start_time_ms"),
        "track_id": row.get("track_id"),
        "payload": row,
        "source": "artifact",
    }


def _bad_case_from_model(row: Any) -> dict[str, Any]:
    payload = row.payload or {}
    return {
        "id": row.id,
        "case_id": row.id,
        "run_id": row.run_id,
        "video_id": payload.get("video_id"),
        "event_id": row.event_id,
        "track_id": payload.get("track_id"),
        "case_type": row.type,
        "module": payload.get("module"),
        "description": row.description or "",
        "expected_result": payload.get("expected_result") or "",
        "actual_result": payload.get("actual_result") or "",
        "tags": row.tags or [],
        "status": row.status,
        "source": payload.get("source"),
    }


def _with_actor_tag(tags: list[str], actor: str | None) -> list[str]:
    if not actor:
        return tags
    tag = f"actor:{actor}"
    if tag not in tags:
        tags.append(tag)
    return tags
