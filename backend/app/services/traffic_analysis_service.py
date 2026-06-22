from typing import Any
import csv
import json
from pathlib import Path


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


traffic_analysis_service = TrafficAnalysisService()


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    public = dict(metadata)
    input_video = public.get("input_video")
    if input_video:
        public["input_video"] = Path(str(input_video)).name
    return public
