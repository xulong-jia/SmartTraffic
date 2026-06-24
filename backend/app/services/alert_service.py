import json
from pathlib import Path
from typing import Any

from app.alerts.contracts import build_alert
from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings


DEFAULT_ALERT_COOLDOWN_MS = 60_000


class AlertService:
    """Minimal alert artifact generator over existing event artifacts."""

    def __init__(
        self,
        artifact_writer: TrafficArtifactWriter | None = None,
    ) -> None:
        self.artifact_writer = artifact_writer

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_5_minimal_alert_center"}

    def generate_alerts(self, *, run_id: str) -> dict[str, Any]:
        writer = self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)
        run_dir = writer.base_dir / run_id
        metadata_path = run_dir / "metadata.json"
        if not metadata_path.is_file():
            raise KeyError(run_id)

        metadata = writer.read_metadata(run_id)
        video_id = str(metadata.get("video_id", ""))
        events = _read_events(run_dir, metadata)
        event_evidence = _read_event_evidence(run_dir, metadata)
        alerts = _build_alerts_from_events(
            events,
            event_evidence=event_evidence,
            run_id=run_id,
            video_id=video_id,
        )
        artifact_paths = writer.write_alert_outputs(
            run_id=run_id,
            video_id=video_id,
            alerts=alerts,
        )
        writer.write_visual_artifacts(run_id)
        writer.write_run_manifest(run_id, status="completed")
        alert_summary = _read_json(artifact_paths["alert_summary"])
        metadata_after = writer.read_metadata(run_id)

        return {
            "run_id": run_id,
            "video_id": video_id,
            "status": "completed",
            "total_alerts": alert_summary["total_alerts"],
            "alert_summary": alert_summary,
            "artifacts": metadata_after.get("artifacts", {}),
        }

    def list_alerts(
        self,
        *,
        run_id: str | None = None,
        status: str | None = None,
        level: str | None = None,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for _, run_dir in self._iter_run_dirs(run_id=run_id):
            metadata = self._read_metadata_path(run_dir)
            if metadata is None:
                continue
            alerts.extend(
                alert
                for alert in _read_alerts(run_dir, metadata)
                if _alert_matches(alert, status=status, level=level)
            )
        return alerts

    def get_alert(self, alert_id: str) -> dict[str, Any]:
        for _, run_dir in self._iter_run_dirs():
            metadata = self._read_metadata_path(run_dir)
            if metadata is None:
                continue
            for alert in _read_alerts(run_dir, metadata):
                if _alert_id(alert) == alert_id:
                    return alert
        raise KeyError(alert_id)

    def acknowledge_alert(
        self,
        alert_id: str,
        *,
        acknowledged_by: str | None = None,
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
            {
                "status": "resolved",
                "resolved_at": _utc_now_iso(),
            },
        )

    def ignore_alert(self, alert_id: str) -> dict[str, Any]:
        return self._update_alert(alert_id, {"status": "ignored"})

    def _update_alert(
        self,
        alert_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        writer = self._writer()
        for run_id, run_dir in self._iter_run_dirs():
            metadata = self._read_metadata_path(run_dir)
            if metadata is None:
                continue
            alerts = _read_alerts(run_dir, metadata)
            for index, alert in enumerate(alerts):
                if _alert_id(alert) != alert_id:
                    continue
                updated = _normalize_alert({**alert, **updates})
                alerts[index] = updated
                writer.write_alert_outputs(
                    run_id=run_id,
                    video_id=str(metadata.get("video_id", updated.get("video_id", ""))),
                    alerts=alerts,
                )
                writer.write_run_manifest(run_id, status="completed")
                return updated
        raise KeyError(alert_id)

    def _iter_run_dirs(
        self,
        *,
        run_id: str | None = None,
    ) -> list[tuple[str, Path]]:
        base_dir = self._writer().base_dir
        if run_id is not None:
            return [(run_id, base_dir / run_id)]
        if not base_dir.is_dir():
            return []
        return [
            (path.name, path)
            for path in sorted(base_dir.iterdir(), key=lambda item: item.name)
            if path.is_dir()
        ]

    def _read_metadata_path(self, run_dir: Path) -> dict[str, Any] | None:
        metadata_path = run_dir / "metadata.json"
        if not metadata_path.is_file():
            return None
        with metadata_path.open(encoding="utf-8") as file:
            return json.load(file)

    def _writer(self) -> TrafficArtifactWriter:
        return self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)


def _read_events(run_dir: Path, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = metadata.get("artifacts", {})
    relative_path = artifacts.get("events_jsonl") or artifacts.get("events") or "events.jsonl"
    events_path = run_dir / str(relative_path)
    if not events_path.is_file():
        raise FileNotFoundError("event artifacts not found")

    events: list[dict[str, Any]] = []
    with events_path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                events.append(json.loads(stripped))
    return events


def _read_event_evidence(
    run_dir: Path,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    artifacts = metadata.get("artifacts", {})
    relative_path = artifacts.get("event_evidence_jsonl") or "event_evidence.jsonl"
    evidence_path = run_dir / str(relative_path)
    if not evidence_path.is_file():
        return []
    return _read_jsonl(evidence_path)


def _read_alerts(run_dir: Path, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = metadata.get("artifacts", {})
    relative_path = artifacts.get("alerts_jsonl") or artifacts.get("alerts") or "alerts.jsonl"
    alerts_path = run_dir / str(relative_path)
    if not alerts_path.is_file():
        return []
    return [_normalize_alert(alert) for alert in _read_jsonl(alerts_path)]


def _build_alerts_from_events(
    events: list[dict[str, Any]],
    *,
    event_evidence: list[dict[str, Any]],
    run_id: str,
    video_id: str,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    seen_alert_ids: set[str] = set()
    last_alert_time_by_key: dict[tuple[str, Any, Any], int | None] = {}
    evidence_by_event_id = _first_evidence_by_event_id(event_evidence)
    for event in events:
        event_id = event.get("event_id")
        if event_id is None:
            continue
        event_type = str(event.get("event_type", "unknown_event"))
        timestamp_ms = _optional_int(
            _first_present(event.get("end_time_ms"), event.get("start_time_ms"))
        )
        dedup_key = (
            event_type,
            _optional_int(event.get("track_id")),
            event.get("zone_id"),
        )
        if _is_in_alert_cooldown(
            dedup_key,
            timestamp_ms,
            last_alert_time_by_key,
        ):
            continue
        evidence = evidence_by_event_id.get(str(event_id), {})
        alert = build_alert(
            event_id=str(event_id),
            run_id=run_id,
            video_id=str(event.get("video_id") or video_id),
            event_type=event_type,
            severity=event.get("severity"),
            track_id=_optional_int(event.get("track_id")),
            zone_id=event.get("zone_id"),
            frame_index=_optional_int(
                _first_present(event.get("end_frame"), event.get("start_frame"))
            ),
            timestamp_ms=_optional_int(
                _first_present(event.get("end_time_ms"), event.get("start_time_ms"))
            ),
            event_evidence_id=evidence.get("evidence_id"),
            snapshot_path=evidence.get("snapshot_path"),
        )
        if alert["alert_id"] in seen_alert_ids:
            continue
        seen_alert_ids.add(alert["alert_id"])
        last_alert_time_by_key[dedup_key] = timestamp_ms
        alerts.append(alert)
    return alerts


def _first_evidence_by_event_id(
    event_evidence: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    evidence_by_event_id: dict[str, dict[str, Any]] = {}
    for evidence in event_evidence:
        event_id = evidence.get("event_id")
        if event_id is None:
            continue
        evidence_by_event_id.setdefault(str(event_id), evidence)
    return evidence_by_event_id


def _is_in_alert_cooldown(
    dedup_key: tuple[str, Any, Any],
    timestamp_ms: int | None,
    last_alert_time_by_key: dict[tuple[str, Any, Any], int | None],
) -> bool:
    if dedup_key not in last_alert_time_by_key:
        return False
    last_timestamp_ms = last_alert_time_by_key[dedup_key]
    if timestamp_ms is None or last_timestamp_ms is None:
        return True
    return timestamp_ms - last_timestamp_ms < DEFAULT_ALERT_COOLDOWN_MS


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _alert_matches(
    alert: dict[str, Any],
    *,
    status: str | None,
    level: str | None,
) -> bool:
    if status is not None and alert.get("status") != status:
        return False
    if level is not None and alert.get("level") != level:
        return False
    return True


def _alert_id(alert: dict[str, Any]) -> str | None:
    value = alert.get("id") or alert.get("alert_id")
    return str(value) if value is not None else None


def _normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(alert)
    alert_id = _alert_id(normalized)
    if alert_id is not None:
        normalized["id"] = alert_id
        normalized["alert_id"] = alert_id
    normalized.setdefault("acknowledged_by", None)
    normalized.setdefault("acknowledged_at", None)
    normalized.setdefault("resolved_at", None)
    normalized.setdefault("event_evidence_id", None)
    normalized.setdefault("snapshot_path", None)
    return normalized


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()
