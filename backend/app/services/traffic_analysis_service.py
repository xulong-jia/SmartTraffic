from typing import Any
import csv
import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter


class TrafficAnalysisService:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def register_run(
        self,
        run_id: str,
        video_id: str,
        result_dir: str,
        artifact_index: dict[str, Any],
        status: str = "completed",
    ) -> dict[str, Any]:
        run = {
            "id": run_id,
            "video_id": video_id,
            "status": status,
            "result_dir": result_dir,
            "artifact_index": artifact_index,
        }
        self._runs[run_id] = run
        return dict(run)

    def list_runs(self) -> list[dict[str, Any]]:
        return list(self._runs.values())

    def get_run(self, run_id: str) -> dict[str, Any]:
        if run_id in self._runs:
            return dict(self._runs[run_id])
        metadata = self._load_metadata(run_id)
        run = {
            "id": run_id,
            "video_id": metadata.get("video_id", ""),
            "status": "completed",
            "result_dir": f"results/traffic_analysis/{run_id}",
            "artifact_index": metadata.get("artifacts", {}),
            "metadata": _public_metadata(metadata),
        }
        self._runs[run_id] = run
        return dict(run)

    def read_run_detections(self, run_id: str, limit: int = 100) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "detection_summary.json"
        jsonl_path = run_dir / "detections.jsonl"
        csv_path = run_dir / "detections.csv"
        summary: dict[str, Any] = {}
        if summary_path.is_file():
            with summary_path.open(encoding="utf-8") as file:
                summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if jsonl_path.is_file():
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if stripped:
                        frames.append(json.loads(stripped))
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
        }

    def read_run_tracks(self, run_id: str, limit: int = 100) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "tracking_summary.json"
        jsonl_path = run_dir / "tracks.jsonl"
        csv_path = run_dir / "tracks.csv"
        summary: dict[str, Any] = {}
        if summary_path.is_file():
            with summary_path.open(encoding="utf-8") as file:
                summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if jsonl_path.is_file():
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if stripped:
                        frames.append(json.loads(stripped))
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
        }

    def read_run_trajectory_points(
        self,
        run_id: str,
        limit: int = 100,
        track_id: int | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "trajectory_summary.json"
        jsonl_path = run_dir / "trajectory_points.jsonl"
        csv_path = run_dir / "trajectory_points.csv"
        if (
            not summary_path.is_file()
            or not jsonl_path.is_file()
            or not csv_path.is_file()
        ):
            raise KeyError(run_id)

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        frames: list[dict[str, Any]] = []
        if limit > 0:
            with jsonl_path.open(encoding="utf-8") as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    frame = json.loads(stripped)
                    if track_id is not None:
                        frame = dict(frame)
                        frame["trajectory_points"] = [
                            point
                            for point in frame.get("trajectory_points", [])
                            if _track_id_matches(point.get("track_id"), track_id)
                        ]
                    frames.append(frame)
                    if len(frames) >= limit:
                        break

        rows: list[dict[str, str]] = []
        if limit > 0:
            with csv_path.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    if track_id is not None and not _track_id_matches(
                        row.get("track_id"),
                        track_id,
                    ):
                        continue
                    rows.append(row)
                    if len(rows) >= limit:
                        break

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "frames": frames,
            "rows": rows,
            "limit": limit,
            "track_id": track_id,
        }

    def read_run_events(
        self,
        run_id: str,
        limit: int = 100,
        event_type: str | None = None,
        track_id: int | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "event_summary.json"
        events_path = run_dir / "events.jsonl"
        evidence_path = run_dir / "event_evidence.jsonl"
        executions_path = run_dir / "rule_executions.jsonl"
        if (
            not summary_path.is_file()
            or not events_path.is_file()
            or not evidence_path.is_file()
            or not executions_path.is_file()
        ):
            raise FileNotFoundError("event artifacts not found")

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        events: list[dict[str, Any]] = []
        event_ids: set[str] | None = None
        if limit > 0:
            for event in _read_jsonl_limited(
                events_path,
                limit=limit,
                predicate=lambda item: _event_matches(
                    item,
                    event_type=event_type,
                    track_id=track_id,
                ),
            ):
                events.append(event)
            if event_type is not None or track_id is not None:
                event_ids = {
                    str(event["event_id"])
                    for event in events
                    if event.get("event_id") is not None
                }

        event_evidence: list[dict[str, Any]] = []
        rule_executions: list[dict[str, Any]] = []
        if limit > 0:
            event_evidence = _read_jsonl_limited(
                evidence_path,
                limit=limit,
                predicate=lambda item: _event_related_record_matches(
                    item,
                    event_ids=event_ids,
                    track_id=track_id,
                ),
            )
            rule_executions = _read_jsonl_limited(
                executions_path,
                limit=limit,
                predicate=lambda item: _event_related_record_matches(
                    item,
                    event_ids=event_ids,
                    track_id=track_id,
                ),
            )

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "events": events,
            "event_evidence": event_evidence,
            "rule_executions": rule_executions,
            "limit": limit,
            "event_type": event_type,
            "track_id": track_id,
        }

    def read_run_alerts(
        self,
        run_id: str,
        limit: int = 100,
        status: str | None = None,
        level: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        metadata = self._load_metadata(run_id)
        summary_path = run_dir / "alert_summary.json"
        alerts_path = run_dir / "alerts.jsonl"
        if not summary_path.is_file() or not alerts_path.is_file():
            raise FileNotFoundError("alert artifacts not found")

        with summary_path.open(encoding="utf-8") as file:
            summary = json.load(file)

        alerts: list[dict[str, Any]] = []
        if limit > 0:
            alerts = _read_jsonl_limited(
                alerts_path,
                limit=limit,
                predicate=lambda item: _alert_matches(
                    item,
                    status=status,
                    level=level,
                    event_type=event_type,
                ),
            )

        return {
            "run_id": run_id,
            "video_id": metadata.get("video_id", ""),
            "summary": summary,
            "alerts": alerts,
            "limit": limit,
            "status": status,
            "level": level,
            "event_type": event_type,
        }

    def read_run_flow_counts(self, run_id: str) -> dict[str, Any]:
        run_dir = self._ensure_statistics_artifacts(run_id)
        flow_counts_path = run_dir / "flow_counts.json"
        if not flow_counts_path.is_file():
            raise FileNotFoundError("flow counts artifact not found")
        with flow_counts_path.open(encoding="utf-8") as file:
            return json.load(file)

    def read_run_zone_statistics(self, run_id: str) -> dict[str, Any]:
        run_dir = self._ensure_statistics_artifacts(run_id)
        zone_statistics_path = run_dir / "zone_statistics.json"
        if not zone_statistics_path.is_file():
            raise FileNotFoundError("zone statistics artifact not found")
        with zone_statistics_path.open(encoding="utf-8") as file:
            return json.load(file)

    def read_run_manifest(self, run_id: str) -> dict[str, Any]:
        metadata = self._load_metadata(run_id)
        writer = TrafficArtifactWriter(self._run_dir(run_id).parent)
        return writer.write_run_manifest(
            run_id,
            status=str(metadata.get("status") or "completed"),
        )

    def clear(self) -> None:
        self._runs.clear()

    def _run_dir(self, run_id: str) -> Path:
        from app.core.config import get_settings

        return get_settings().results_dir / run_id

    def _load_metadata(self, run_id: str) -> dict[str, Any]:
        metadata_path = self._run_dir(run_id) / "metadata.json"
        if not metadata_path.is_file():
            raise KeyError(run_id)
        with metadata_path.open(encoding="utf-8") as file:
            return json.load(file)

    def _ensure_statistics_artifacts(self, run_id: str) -> Path:
        metadata = self._load_metadata(run_id)
        run_dir = self._run_dir(run_id)
        writer = TrafficArtifactWriter(run_dir.parent)
        if not (run_dir / "flow_counts.json").is_file() or not (
            run_dir / "zone_statistics.json"
        ).is_file():
            writer.write_statistics_outputs(run_id)
        else:
            writer.write_run_manifest(
                run_id,
                status=str(metadata.get("status") or "completed"),
            )
        return run_dir


traffic_analysis_service = TrafficAnalysisService()


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    public = dict(metadata)
    input_video = public.get("input_video")
    if input_video:
        public["input_video"] = Path(str(input_video)).name
    return public


def _track_id_matches(value: Any, track_id: int) -> bool:
    try:
        return int(value) == track_id
    except (TypeError, ValueError):
        return False


def _read_jsonl_limited(
    path: Path,
    *,
    limit: int,
    predicate,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not predicate(row):
                continue
            rows.append(row)
            if len(rows) >= limit:
                break
    return rows


def _event_matches(
    event: dict[str, Any],
    *,
    event_type: str | None,
    track_id: int | None,
) -> bool:
    if event_type is not None and event.get("event_type") != event_type:
        return False
    if track_id is not None and not _track_id_matches(event.get("track_id"), track_id):
        return False
    return True


def _event_related_record_matches(
    row: dict[str, Any],
    *,
    event_ids: set[str] | None,
    track_id: int | None,
) -> bool:
    if event_ids is not None:
        event_id = row.get("event_id")
        if event_id is None or str(event_id) not in event_ids:
            return False
    if track_id is not None and not _track_id_matches(row.get("track_id"), track_id):
        return False
    return True


def _alert_matches(
    alert: dict[str, Any],
    *,
    status: str | None,
    level: str | None,
    event_type: str | None,
) -> bool:
    if status is not None and alert.get("status") != status:
        return False
    if level is not None and alert.get("level") != level:
        return False
    if event_type is not None and alert.get("event_type") != event_type:
        return False
    return True
