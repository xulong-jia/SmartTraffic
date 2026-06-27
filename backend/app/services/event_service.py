from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.core.config import get_settings
from app.events.engine import EventEngine
from app.services.event_rule_service import event_rule_service


@dataclass(frozen=True)
class EventRunParams:
    rules: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None
    source: dict[str, str] | None = None
    config_snapshot: dict[str, Any] | None = None
    record_not_matched: bool = False


class EventService:
    """Stage-five event pipeline over existing trajectory artifacts."""

    def __init__(
        self,
        artifact_writer: TrafficArtifactWriter | None = None,
    ) -> None:
        self.artifact_writer = artifact_writer

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_5_event_query_pipeline"}

    def run_events(
        self,
        *,
        run_id: str,
        video_id: str | None = None,
        params: EventRunParams | None = None,
    ) -> dict[str, Any]:
        effective_params = params or EventRunParams()
        writer = self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)
        metadata = writer.read_metadata(run_id)
        effective_video_id = video_id or str(metadata.get("video_id", ""))
        trajectory_frames = _read_trajectory_frames(
            writer.base_dir / run_id,
            metadata,
        )

        config = _resolve_event_config(
            video_id=effective_video_id,
            params=effective_params,
        )
        engine = EventEngine(
            run_id=run_id,
            video_id=effective_video_id,
            record_not_matched=effective_params.record_not_matched,
        )
        event_output = engine.evaluate(
            trajectory_frames,
            rules=config["event_rules"],
            zones=config["zones"],
        )
        artifact_paths = writer.write_event_outputs(
            run_id=run_id,
            video_id=effective_video_id,
            events=event_output["events"],
            event_evidence=event_output["event_evidence"],
            rule_executions=event_output["rule_executions"],
        )
        writer.update_metadata(
            run_id,
            {
                "event_config_snapshot": effective_params.config_snapshot or {
                    "source": config["source"],
                    "zones": config["zones"],
                    "event_rules": config["event_rules"],
                },
                "enabled_rules_count": _enabled_count(config["event_rules"]),
                "enabled_zones_count": _enabled_count(config["zones"]),
                "events_count": len(event_output["events"]),
                "event_evidence_count": len(event_output["event_evidence"]),
                "rule_executions_count": len(event_output["rule_executions"]),
                "alerts_count": 0,
            },
        )
        writer.write_statistics_outputs(run_id)
        writer.write_visual_artifacts(run_id)
        event_summary = _read_json(artifact_paths["event_summary"])
        metadata_after = writer.read_metadata(run_id)

        return {
            "run_id": run_id,
            "video_id": effective_video_id,
            "status": "completed",
            "total_events": event_summary["total_events"],
            "event_summary": event_summary,
            "artifacts": metadata_after.get("artifacts", {}),
        }


def _read_trajectory_frames(
    run_dir: Path,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    artifacts = metadata.get("artifacts", {})
    relative_path = artifacts.get("trajectory_points_jsonl") or "trajectory_points.jsonl"
    trajectory_path = run_dir / str(relative_path)
    if not trajectory_path.is_file():
        raise FileNotFoundError("trajectory artifacts not found")

    frames: list[dict[str, Any]] = []
    with trajectory_path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                frames.append(json.loads(stripped))
    return frames


def _resolve_event_config(
    *,
    video_id: str,
    params: EventRunParams,
) -> dict[str, Any]:
    request_zones = params.zones
    request_rules = params.rules
    source = params.source or {
        "zones": "request" if request_zones is not None else "service",
        "rules": "request" if request_rules is not None else "service",
    }
    config = event_rule_service.build_event_engine_config(
        video_id=video_id,
        zones=request_zones,
        rules=request_rules,
    )
    config["source"] = source
    return config


def _enabled_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("enabled", True))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)
