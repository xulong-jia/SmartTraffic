import json
from pathlib import Path
from typing import Any

from app.alerts.contracts import build_alert
from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings


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
        alerts = _build_alerts_from_events(events, run_id=run_id, video_id=video_id)
        artifact_paths = writer.write_alert_outputs(
            run_id=run_id,
            video_id=video_id,
            alerts=alerts,
        )
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


def _build_alerts_from_events(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    video_id: str,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    seen_alert_ids: set[str] = set()
    for event in events:
        event_id = event.get("event_id")
        if event_id is None:
            continue
        event_type = str(event.get("event_type", "unknown_event"))
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
        )
        if alert["alert_id"] in seen_alert_ids:
            continue
        seen_alert_ids.add(alert["alert_id"])
        alerts.append(alert)
    return alerts


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


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)
