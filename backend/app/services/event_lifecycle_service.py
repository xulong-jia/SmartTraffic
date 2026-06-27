from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.alerts.contracts import build_alert
from app.events.engine import EventEngine
from app.repositories import (
    AlertRepository,
    EventEvidenceRepository,
    EventRepository,
    ProcessingTaskRepository,
    ReviewCommentRepository,
    RuleExecutionRepository,
    TrafficAnalysisRunRepository,
    TrajectoryPointRepository,
)
from app.services.event_rule_service import EventRuleDbService


REVIEW_ACTION_TO_STATUS = {
    "confirm": "confirmed",
    "mark_false_positive": "false_positive",
    "ignore": "ignored",
    "resolve": "resolved",
}


class EventLifecycleService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.event_evidence = EventEvidenceRepository(session)
        self.rule_executions = RuleExecutionRepository(session)
        self.alerts = AlertRepository(session)
        self.review_comments = ReviewCommentRepository(session)
        self.tasks = ProcessingTaskRepository(session)
        self.runs = TrafficAnalysisRunRepository(session)
        self.trajectory_points = TrajectoryPointRepository(session)

    def create_event_with_evidence(
        self,
        *,
        run_id: str,
        video_id: str | None,
        event_id: str | None = None,
        event_type: str,
        status: str = "pending",
        severity: str | None = None,
        track_id: str | int | None = None,
        frame_index: int | None = None,
        timestamp_ms: float | None = None,
        rule_id: str | None = None,
        zone_id: str | None = None,
        payload: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        row = self.events.create(
            id=event_id or f"event_{uuid4().hex[:12]}",
            run_id=run_id,
            video_id=video_id,
            rule_id=rule_id,
            zone_id=zone_id,
            type=event_type,
            status=status,
            severity=severity,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            track_id=str(track_id) if track_id is not None else None,
            payload=dict(payload or {}),
        )
        for item in evidence or []:
            self.event_evidence.create(
                id=str(item.get("id") or f"evidence_{uuid4().hex[:12]}"),
                event_id=row.id,
                run_id=run_id,
                evidence_type=str(item.get("evidence_type") or "event_evidence"),
                payload=dict(item.get("payload") or {}),
                artifact_path=item.get("artifact_path"),
            )
        return _event_from_model(row)

    def create_rule_execution(
        self,
        *,
        run_id: str,
        rule_id: str | None,
        event_id: str | None = None,
        status: str = "matched",
        matched_count: int = 0,
        details: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(details or {})
        if event_id is not None:
            payload.setdefault("event_id", event_id)
        row = self.rule_executions.create(
            id=f"rule_exec_{uuid4().hex[:12]}",
            run_id=run_id,
            rule_id=rule_id,
            status=status,
            matched_count=matched_count,
            details=payload,
            error_message=error_message,
        )
        return _rule_execution_from_model(row)

    def create_alert_for_event(self, event_id: str) -> dict[str, Any]:
        event = self.events.get(event_id)
        if event is None:
            raise KeyError(event_id)
        evidence = self.event_evidence.list(event_id=event.id)
        first_evidence = evidence[0] if evidence else None
        alert = build_alert(
            event_id=event.id,
            run_id=event.run_id,
            video_id=event.video_id or "",
            event_type=event.type,
            severity=event.severity,
            track_id=_optional_int(event.track_id),
            frame_index=event.frame_index,
            timestamp_ms=_optional_int(event.timestamp_ms),
            zone_id=event.zone_id,
            event_evidence_id=first_evidence.id if first_evidence is not None else None,
            snapshot_path=(
                first_evidence.artifact_path if first_evidence is not None else None
            ),
        )
        row = self.alerts.create(
            id=alert["id"],
            run_id=event.run_id,
            event_id=event.id,
            type=alert["alert_type"],
            status=alert["status"],
            severity=alert["level"],
            message=alert["message"],
            payload=alert,
        )
        return _alert_from_model(row)

    def list_alerts(
        self,
        *,
        run_id: str | None = None,
        status: str | None = None,
        level: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.alerts.list(run_id=run_id, status=status, severity=level)
        return [_alert_from_model(row) for row in rows]

    def get_alert(self, alert_id: str) -> dict[str, Any]:
        row = self.alerts.get(alert_id)
        if row is None:
            raise KeyError(alert_id)
        return _alert_from_model(row)

    def acknowledge_alert(
        self,
        alert_id: str,
        *,
        acknowledged_by: str | None,
    ) -> dict[str, Any]:
        return self._update_alert(
            alert_id,
            {
                "status": "acknowledged",
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": _utc_now_iso(),
            },
        )

    def resolve_alert(self, alert_id: str) -> dict[str, Any]:
        return self._update_alert(
            alert_id,
            {"status": "resolved", "resolved_at": _utc_now_iso()},
        )

    def ignore_alert(self, alert_id: str) -> dict[str, Any]:
        return self._update_alert(alert_id, {"status": "ignored"})

    def list_review_events(
        self,
        *,
        run_id: str,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self.events.list(run_id=run_id, type=event_type)
        items = [_review_event_item(row) for row in rows]
        if status is not None:
            items = [item for item in items if item["review_status"] == status]
        for item in items:
            comments = self.review_comments.list(event_id=item["event_id"])
            alerts = self.alerts.list(event_id=item["event_id"])
            item["comment_count"] = len(comments)
            item["linked_alert_ids"] = [alert.id for alert in alerts]
            if comments:
                item["last_action"] = _review_record_from_model(comments[-1])["action"]
        total = len(items)
        return {
            "items": items[offset : offset + limit] if limit > 0 else [],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_review_event(self, *, run_id: str, event_id: str) -> dict[str, Any]:
        event = self.events.get(event_id)
        if event is None or event.run_id != run_id:
            raise KeyError(event_id)
        comments = [
            _review_record_from_model(row)
            for row in self.review_comments.list(event_id=event_id)
        ]
        alerts = [_alert_from_model(row) for row in self.alerts.list(event_id=event_id)]
        evidence = [
            _evidence_from_model(row)
            for row in self.event_evidence.list(event_id=event_id)
        ]
        rule_executions = [
            _rule_execution_from_model(row)
            for row in self.rule_executions.list(run_id=run_id)
            if _rule_execution_matches_event(row, event_id)
        ]
        return {
            "run_id": run_id,
            "event": _event_from_model(event),
            "review_state": _review_state(run_id, event_id, event.status, comments),
            "event_evidence": evidence,
            "rule_executions": rule_executions,
            "linked_alerts": alerts,
            "comments": comments,
            "visual_artifacts": {},
        }

    def apply_review_action(
        self,
        *,
        run_id: str,
        event_id: str,
        action: str,
        comment: str = "",
        reviewer: str = "local_reviewer",
        alert_id: str | None = None,
    ) -> dict[str, Any]:
        event = self.events.get(event_id)
        if event is None or event.run_id != run_id:
            raise KeyError(event_id)
        before_status = event.status
        after_status = REVIEW_ACTION_TO_STATUS.get(action, before_status)
        if after_status != before_status:
            event = self.events.update_status(event_id, after_status)
            if event is None:
                raise KeyError(event_id)
        review = self._create_review_record(
            run_id=run_id,
            event_id=event_id,
            action=action,
            before_status=before_status,
            after_status=after_status,
            comment=comment,
            reviewer=reviewer,
            alert_id=alert_id,
        )
        return _review_action_response(
            run_id=run_id,
            event_id=event_id,
            status=after_status,
            review=review,
        )

    def query_review_comments(
        self,
        *,
        run_id: str,
        event_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self.review_comments.list(run_id=run_id, event_id=event_id)
        items = [_review_record_from_model(row) for row in rows]
        total = len(items)
        return {
            "run_id": run_id,
            "event_id": event_id,
            "items": items[offset : offset + limit] if limit > 0 else [],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def add_false_negative(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        event_id = f"fn_{uuid4().hex[:12]}"
        event = self.events.create(
            id=event_id,
            run_id=run_id,
            video_id=run.video_id,
            rule_id=None,
            zone_id=record.get("zone_id"),
            type=str(record.get("expected_event_type") or "false_negative"),
            status="false_negative",
            severity="medium",
            frame_index=record.get("start_frame"),
            timestamp_ms=record.get("start_time_ms"),
            track_id=(
                str(record["track_id"]) if record.get("track_id") is not None else None
            ),
            payload=dict(record),
        )
        false_negative = {
            "false_negative_id": event.id,
            "run_id": run_id,
            "expected_event_type": event.type,
            "zone_id": event.zone_id,
            "track_id": _optional_int(event.track_id),
            "start_frame": record.get("start_frame"),
            "end_frame": record.get("end_frame"),
            "start_time_ms": record.get("start_time_ms"),
            "end_time_ms": record.get("end_time_ms"),
            "description": str(record.get("description") or ""),
            "reviewer": str(record.get("reviewer") or "local_reviewer"),
            "created_at": _datetime_iso(event.created_at),
            "status": "false_negative",
            "source": "review_center",
        }
        review = self._create_review_record(
            run_id=run_id,
            event_id=event.id,
            action="add_false_negative",
            before_status=None,
            after_status="false_negative",
            comment=false_negative["description"],
            reviewer=false_negative["reviewer"],
            alert_id=None,
        )
        return {
            "run_id": run_id,
            "event_id": event.id,
            "status": "false_negative",
            "false_negative": false_negative,
            "review": review,
            "state": _review_state(run_id, event.id, "false_negative", [review]),
        }

    def create_rule_rerun_request(
        self,
        *,
        run_id: str,
        event_id: str,
        reviewer: str = "local_reviewer",
        comment: str = "",
        rule_id: str | None = None,
    ) -> dict[str, Any]:
        event = self.events.get(event_id)
        if event is None or event.run_id != run_id:
            raise KeyError(event_id)
        run = self.runs.get(run_id)
        video_id = event.video_id or (run.video_id if run is not None else None)
        if video_id is None:
            raise KeyError("video_id")
        selected_rule_id = rule_id or event.rule_id
        task = self.tasks.create(
            id=f"task_{uuid4().hex[:12]}",
            video_id=video_id,
            status="pending",
            mode="rule_rerun",
            parameters={
                "event_id": event_id,
                "run_id": run_id,
                "rule_id": selected_rule_id,
                "rerun_scope": "event_rules_only",
                "requested_by": reviewer,
                "reason": comment,
            },
            progress=0.0,
            result=None,
            error_message=None,
        )
        result = self._execute_event_rule_rerun(
            run=run,
            task_id=task.id,
            run_id=run_id,
            video_id=video_id,
            event_id=event_id,
            selected_rule_id=selected_rule_id,
        )
        if result is not None:
            task = self.tasks.update_status(
                task.id,
                "completed",
                progress=1.0,
                result=result,
                finished_at=datetime.now(UTC),
            ) or task
        return {
            "run_id": run_id,
            "event_id": event_id,
            "status": task.status,
            "task_id": task.id,
            "mode": task.mode,
            "parameters": task.parameters or {},
            "rerun_scope": "event_rules_only",
            "result": task.result,
        }

    def has_db_events(self, *, run_id: str | None = None) -> bool:
        return bool(self.events.list(run_id=run_id))

    def has_db_event(self, event_id: str, *, run_id: str | None = None) -> bool:
        row = self.events.get(event_id)
        return row is not None and (run_id is None or row.run_id == run_id)

    def has_db_review_comments(
        self,
        *,
        run_id: str,
        event_id: str | None = None,
    ) -> bool:
        return bool(self.review_comments.list(run_id=run_id, event_id=event_id))

    def _update_alert(self, alert_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        row = self.alerts.get(alert_id)
        if row is None:
            raise KeyError(alert_id)
        payload = {**dict(row.payload or {}), **updates}
        updated = self.alerts.update(
            alert_id,
            status=str(payload["status"]),
            severity=payload.get("level") or row.severity,
            message=payload.get("message") or row.message,
            payload=payload,
        )
        if updated is None:
            raise KeyError(alert_id)
        return _alert_from_model(updated)

    def _create_review_record(
        self,
        *,
        run_id: str,
        event_id: str | None,
        action: str,
        before_status: str | None,
        after_status: str,
        comment: str,
        reviewer: str,
        alert_id: str | None,
    ) -> dict[str, Any]:
        created_at = _utc_now_iso()
        review_id = f"review_{uuid4().hex[:12]}"
        payload = {
            "review_id": review_id,
            "run_id": run_id,
            "event_id": event_id,
            "alert_id": alert_id,
            "action": action,
            "before_status": before_status,
            "after_status": after_status,
            "comment": comment,
            "reviewer": reviewer,
            "created_at": created_at,
            "source": "review_center",
        }
        row = self.review_comments.create(
            id=review_id,
            run_id=run_id,
            event_id=event_id,
            author=reviewer,
            status=after_status,
            body=comment,
            payload=payload,
        )
        return _review_record_from_model(row)

    def _execute_event_rule_rerun(
        self,
        *,
        run: Any | None,
        task_id: str,
        run_id: str,
        video_id: str,
        event_id: str,
        selected_rule_id: str | None,
    ) -> dict[str, Any] | None:
        config = self._event_engine_config(
            run=run,
            video_id=video_id,
            selected_rule_id=selected_rule_id,
        )
        rules = config["event_rules"]
        frames = _trajectory_frames_from_rows(
            self.trajectory_points.list(run_id=run_id)
        )
        if not rules or not frames:
            return None

        output = EventEngine(
            run_id=run_id,
            video_id=video_id,
            record_not_matched=True,
        ).evaluate(frames, rules=rules, zones=config["zones"])
        return self._persist_rerun_output(
            task_id=task_id,
            run_id=run_id,
            video_id=video_id,
            event_id=event_id,
            output=output,
            trajectory_frame_count=len(frames),
            rule_count=len(rules),
        )

    def _event_engine_config(
        self,
        *,
        run: Any | None,
        video_id: str,
        selected_rule_id: str | None,
    ) -> dict[str, list[dict[str, Any]]]:
        snapshot = _event_config_snapshot(run)
        if snapshot is not None:
            config = EventRuleDbService(self.session).build_event_engine_config(
                video_id=video_id,
                zones=_config_items(snapshot.get("zones")),
                rules=_config_items(snapshot.get("event_rules")),
            )
        else:
            config = EventRuleDbService(self.session).build_event_engine_config(
                video_id=video_id,
            )
        if selected_rule_id is None:
            return config
        filtered_rules = [
            rule
            for rule in config["event_rules"]
            if str(rule.get("rule_id") or rule.get("id")) == str(selected_rule_id)
        ]
        if filtered_rules:
            config = {**config, "event_rules": filtered_rules}
        return config

    def _persist_rerun_output(
        self,
        *,
        task_id: str,
        run_id: str,
        video_id: str,
        event_id: str,
        output: dict[str, Any],
        trajectory_frame_count: int,
        rule_count: int,
    ) -> dict[str, Any]:
        source_to_rerun_event_id: dict[str, str] = {}
        generated_event_ids: list[str] = []
        for index, event in enumerate(output.get("events") or []):
            if not isinstance(event, dict):
                continue
            rerun_event_id = f"rerun_{task_id}_{index:04d}"
            source_event_id = str(event.get("event_id") or rerun_event_id)
            source_to_rerun_event_id[source_event_id] = rerun_event_id
            generated_event_ids.append(rerun_event_id)
            payload = dict(event)
            payload.update(
                {
                    "source_event_id": source_event_id,
                    "rerun_source_event_id": event_id,
                    "rerun_task_id": task_id,
                    "rerun_scope": "event_rules_only",
                }
            )
            self.events.create(
                id=rerun_event_id,
                run_id=run_id,
                video_id=str(event.get("video_id") or video_id),
                rule_id=event.get("rule_id"),
                zone_id=event.get("zone_id"),
                type=str(event.get("event_type") or "rule_rerun"),
                status=str(event.get("status") or "pending"),
                severity=event.get("severity"),
                frame_index=_optional_int(
                    event.get("end_frame") or event.get("start_frame")
                ),
                timestamp_ms=_optional_float(
                    event.get("end_time_ms") or event.get("start_time_ms")
                ),
                track_id=(
                    str(event["track_id"]) if event.get("track_id") is not None else None
                ),
                payload=payload,
            )

        generated_evidence_ids: list[str] = []
        for index, evidence in enumerate(output.get("event_evidence") or []):
            if not isinstance(evidence, dict):
                continue
            source_event_id = str(evidence.get("event_id") or "")
            rerun_event_id = source_to_rerun_event_id.get(source_event_id)
            if rerun_event_id is None:
                continue
            evidence_id = f"rerun_{task_id}_evidence_{index:04d}"
            payload = dict(evidence)
            payload.update(
                {
                    "source_event_id": source_event_id,
                    "rerun_task_id": task_id,
                    "rerun_scope": "event_rules_only",
                }
            )
            self.event_evidence.create(
                id=evidence_id,
                event_id=rerun_event_id,
                run_id=run_id,
                evidence_type=str(evidence.get("evidence_type") or "rule"),
                payload=payload,
                artifact_path=evidence.get("snapshot_path"),
            )
            generated_evidence_ids.append(evidence_id)

        generated_execution_ids: list[str] = []
        for index, execution in enumerate(output.get("rule_executions") or []):
            if not isinstance(execution, dict):
                continue
            execution_id = f"rerun_{task_id}_exec_{index:04d}"
            source_event_id = str(execution.get("event_id") or "")
            details = dict(execution)
            if source_event_id in source_to_rerun_event_id:
                details["event_id"] = source_to_rerun_event_id[source_event_id]
                details["source_event_id"] = source_event_id
            details.update(
                {
                    "rerun_source_event_id": event_id,
                    "rerun_task_id": task_id,
                    "rerun_scope": "event_rules_only",
                }
            )
            status = str(execution.get("status") or "skipped")
            self.rule_executions.create(
                id=execution_id,
                run_id=run_id,
                rule_id=execution.get("rule_id"),
                status=status,
                matched_count=1 if status == "matched" else 0,
                details=details,
                error_message=(
                    str(execution.get("error_message"))
                    if execution.get("error_message") is not None
                    else None
                ),
            )
            generated_execution_ids.append(execution_id)

        return {
            "task_type": "rule_rerun",
            "rerun_scope": "event_rules_only",
            "run_id": run_id,
            "source_event_id": event_id,
            "trajectory_frame_count": trajectory_frame_count,
            "rule_count": rule_count,
            "generated_event_count": len(generated_event_ids),
            "generated_evidence_count": len(generated_evidence_ids),
            "generated_rule_execution_count": len(generated_execution_ids),
            "generated_event_ids": generated_event_ids,
            "summary": dict(output.get("summary") or {}),
        }


def _event_from_model(row: Any) -> dict[str, Any]:
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
        "payload": row.payload or {},
        "source": "db",
    }


def _evidence_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    result = dict(payload)
    result.update(
        {
            "id": row.id,
            "evidence_id": row.id,
            "event_id": row.event_id,
            "run_id": row.run_id,
            "video_id": payload.get("video_id"),
            "track_id": payload.get("track_id"),
            "frame_index": payload.get("frame_index"),
            "timestamp_ms": payload.get("timestamp_ms"),
            "event_type": payload.get("event_type"),
            "zone_id": payload.get("zone_id"),
            "rule_id": payload.get("rule_id"),
            "evidence_type": row.evidence_type,
            "evidence_json": payload.get("evidence_json") or {},
            "snapshot_path": payload.get("snapshot_path") or row.artifact_path,
            "payload": payload,
            "artifact_path": row.artifact_path,
            "source": "db",
        }
    )
    return result


def _rule_execution_from_model(row: Any) -> dict[str, Any]:
    details = dict(row.details or {})
    result = dict(details)
    result.update(
        {
            "id": row.id,
            "execution_id": row.id,
            "run_id": row.run_id,
            "rule_id": row.rule_id,
            "event_id": details.get("event_id"),
            "track_id": details.get("track_id"),
            "frame_index": details.get("frame_index"),
            "status": row.status,
            "matched_count": row.matched_count,
            "input_features": details.get("input_features") or {},
            "output_result": details.get("output_result") or {},
            "details": details,
            "error_message": row.error_message,
            "created_at": _datetime_iso(row.created_at),
            "source": "db",
        }
    )
    return result


def _rule_execution_matches_event(row: Any, event_id: str) -> bool:
    details = row.details or {}
    if details.get("event_id") is not None:
        return str(details["event_id"]) == event_id
    event_ids = details.get("event_ids")
    if isinstance(event_ids, list):
        return event_id in {str(value) for value in event_ids}
    return False


def _alert_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.setdefault("id", row.id)
    payload.setdefault("alert_id", row.id)
    payload.setdefault("event_id", row.event_id or "")
    payload.setdefault("run_id", row.run_id)
    payload.setdefault("alert_type", row.type)
    payload.setdefault("event_type", row.type)
    payload.setdefault("level", row.severity or "warning")
    payload.setdefault("status", row.status)
    payload.setdefault("message", row.message or "")
    payload.setdefault("title", row.type.replace("_", " ").capitalize())
    payload.setdefault("video_id", "")
    payload.setdefault("created_at", _datetime_iso(row.created_at))
    payload.setdefault("acknowledged_by", None)
    payload.setdefault("acknowledged_at", None)
    payload.setdefault("resolved_at", None)
    payload.setdefault("event_evidence_id", None)
    payload.setdefault("snapshot_path", None)
    return payload


def _review_event_item(row: Any) -> dict[str, Any]:
    return {
        "run_id": row.run_id,
        "event_id": row.id,
        "event_type": row.type,
        "track_id": _optional_int(row.track_id),
        "zone_id": row.zone_id,
        "severity": row.severity,
        "original_status": row.status,
        "review_status": row.status,
        "last_action": None,
        "comment_count": 0,
        "linked_alert_ids": [],
        "start_frame": row.frame_index,
        "end_frame": row.frame_index,
        "start_time_ms": _optional_int(row.timestamp_ms),
        "end_time_ms": _optional_int(row.timestamp_ms),
    }


def _review_record_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.setdefault("review_id", row.id)
    payload.setdefault("run_id", row.run_id)
    payload.setdefault("event_id", row.event_id)
    payload.setdefault("alert_id", None)
    payload.setdefault("action", "comment")
    payload.setdefault("before_status", None)
    payload.setdefault("after_status", row.status)
    payload.setdefault("comment", row.body)
    payload.setdefault("reviewer", row.author or "local_reviewer")
    payload.setdefault("created_at", _datetime_iso(row.created_at))
    payload.setdefault("source", "review_center")
    return payload


def _review_action_response(
    *,
    run_id: str,
    event_id: str,
    status: str,
    review: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "event_id": event_id,
        "status": status,
        "review_id": review["review_id"],
        "review": review,
        "state": _review_state(run_id, event_id, status, [review]),
    }


def _review_state(
    run_id: str,
    event_id: str,
    status: str,
    comments: list[dict[str, Any]],
) -> dict[str, Any]:
    last = comments[-1] if comments else None
    return {
        "schema_version": "stage7b.v1",
        "run_id": run_id,
        "updated_at": last.get("created_at") if last else None,
        "events": {
            event_id: {
                "event_id": event_id,
                "status": status,
                "last_action": last.get("action") if last else "comment",
                "last_review_id": last.get("review_id") if last else "",
                "reviewer": (
                    last.get("reviewer") if last else "local_reviewer"
                ),
                "updated_at": last.get("created_at") if last else _utc_now_iso(),
                "comment_count": len(comments),
            }
        },
    }


def _event_config_snapshot(run: Any | None) -> dict[str, Any] | None:
    if run is None:
        return None
    summary = run.summary or {}
    if not isinstance(summary, dict):
        return None
    snapshot = summary.get("event_config_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    if isinstance(summary.get("zones"), list) or isinstance(summary.get("event_rules"), list):
        return summary
    return None


def _config_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _trajectory_frames_from_rows(rows: list[Any]) -> list[dict[str, Any]]:
    frames_by_key: dict[tuple[int, float | None], dict[str, Any]] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            int(item.frame_index),
            float(item.timestamp_ms or 0.0),
            str(item.track_id),
        ),
    ):
        key = (int(row.frame_index), _optional_float(row.timestamp_ms))
        frame = frames_by_key.setdefault(
            key,
            {
                "frame_index": int(row.frame_index),
                "timestamp_ms": _optional_float(row.timestamp_ms),
                "trajectory_points": [],
            },
        )
        frame["trajectory_points"].append(_trajectory_point_from_row(row))
    return list(frames_by_key.values())


def _trajectory_point_from_row(row: Any) -> dict[str, Any]:
    features = dict(row.features or {})
    point = dict(features)
    point.setdefault("track_id", _optional_int(row.track_id) or str(row.track_id))
    point.setdefault("frame_index", int(row.frame_index))
    point.setdefault("timestamp_ms", _optional_float(row.timestamp_ms))
    point.setdefault("x", float(row.x))
    point.setdefault("y", float(row.y))
    point.setdefault("center", [float(row.x), float(row.y)])
    point.setdefault("bottom_center", [float(row.x), float(row.y)])
    point.setdefault("track_length", int(features.get("track_length") or 1))
    if row.speed is not None:
        point.setdefault("speed_px_per_second", _optional_float(row.speed))
    moving_angle = _optional_float(row.direction)
    if moving_angle is not None:
        point.setdefault("moving_angle", moving_angle)
    return point


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _datetime_iso(value: datetime | None) -> str:
    if value is None:
        return _utc_now_iso()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).replace(microsecond=0).isoformat()
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
