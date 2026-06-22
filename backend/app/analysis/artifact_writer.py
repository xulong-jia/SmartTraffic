import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CORE_ARTIFACTS = {
    "detections": "detections.csv",
    "tracks": "tracks.csv",
    "trajectory_points": "trajectory_points.csv",
    "events": "events.jsonl",
    "alerts": "alerts.jsonl",
    "flow_counts": "flow_counts.json",
    "zone_statistics": "zone_statistics.json",
    "evaluation_summary": "evaluation_summary.json",
    "annotated_video": "annotated_video.mp4",
    "keyframes": "keyframes",
}


class TrafficArtifactWriter:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def create_run_directory(
        self,
        run_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "keyframes").mkdir(exist_ok=True)
        self.write_metadata(run_id, metadata or {})
        return run_dir

    def write_metadata(self, run_id: str, metadata: dict[str, Any]) -> Path:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": run_id,
            "created_at": _utc_now_iso(),
            "artifacts": dict(CORE_ARTIFACTS),
        }
        payload.update(metadata)
        return _write_json(payload, run_dir / "metadata.json")

    def artifact_index(self, run_id: str) -> dict[str, str]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        return {
            name: str(run_dir / relative_path)
            for name, relative_path in CORE_ARTIFACTS.items()
        }


def _write_json(data: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _validate_run_id(run_id: str) -> None:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be a safe directory name")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
