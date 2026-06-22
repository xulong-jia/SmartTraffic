import json
import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CORE_ARTIFACTS = {
    "detections": "detections.csv",
    "detections_csv": "detections.csv",
    "detections_jsonl": "detections.jsonl",
    "detection_summary": "detection_summary.json",
    "detection_preview": "detection_preview.mp4",
    "tracks": "tracks.csv",
    "tracks_csv": "tracks.csv",
    "tracks_jsonl": "tracks.jsonl",
    "tracking_summary": "tracking_summary.json",
    "tracking_preview": "tracking_preview.mp4",
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

    def read_metadata(self, run_id: str) -> dict[str, Any]:
        _validate_run_id(run_id)
        metadata_path = self.base_dir / run_id / "metadata.json"
        with metadata_path.open(encoding="utf-8") as file:
            return json.load(file)

    def update_metadata(self, run_id: str, updates: dict[str, Any]) -> Path:
        metadata = self.read_metadata(run_id)
        metadata.update(updates)
        return self.write_metadata(run_id, metadata)

    def write_detection_outputs(
        self,
        run_id: str,
        video_id: str,
        frame_results: list[dict[str, Any]],
    ) -> dict[str, Path]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        detections_csv = run_dir / "detections.csv"
        detections_jsonl = run_dir / "detections.jsonl"
        detection_summary = run_dir / "detection_summary.json"

        with detections_csv.open("w", newline="", encoding="utf-8") as file:
            fieldnames = [
                "run_id",
                "video_id",
                "frame_index",
                "timestamp_ms",
                "class_id",
                "class_name",
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for frame_result in frame_results:
                for detection in frame_result.get("detections", []):
                    x1, y1, x2, y2 = [float(value) for value in detection["bbox"]]
                    writer.writerow(
                        {
                            "run_id": run_id,
                            "video_id": video_id,
                            "frame_index": frame_result["frame_index"],
                            "timestamp_ms": frame_result.get("timestamp_ms"),
                            "class_id": detection.get("class_id"),
                            "class_name": detection["class_name"],
                            "confidence": detection["confidence"],
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                        }
                    )

        with detections_jsonl.open("w", encoding="utf-8") as file:
            for frame_result in frame_results:
                file.write(json.dumps(frame_result, ensure_ascii=False))
                file.write("\n")

        summary = build_detection_summary(frame_results)
        _write_json(summary, detection_summary)
        return {
            "detections_csv": detections_csv,
            "detections_jsonl": detections_jsonl,
            "detection_summary": detection_summary,
        }

    def write_tracking_outputs(
        self,
        run_id: str,
        video_id: str,
        frame_results: list[dict[str, Any]],
    ) -> dict[str, Path]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        tracks_csv = run_dir / "tracks.csv"
        tracks_jsonl = run_dir / "tracks.jsonl"
        tracking_summary = run_dir / "tracking_summary.json"

        with tracks_csv.open("w", newline="", encoding="utf-8") as file:
            fieldnames = [
                "run_id",
                "video_id",
                "frame_index",
                "timestamp_ms",
                "track_id",
                "class_id",
                "class_name",
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2",
                "center_x",
                "center_y",
                "state",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for frame_result in frame_results:
                for track in frame_result.get("tracks", []):
                    x1, y1, x2, y2 = [float(value) for value in track["bbox"]]
                    center_x, center_y = [float(value) for value in track["center"]]
                    writer.writerow(
                        {
                            "run_id": run_id,
                            "video_id": video_id,
                            "frame_index": frame_result["frame_index"],
                            "timestamp_ms": frame_result.get("timestamp_ms"),
                            "track_id": track["track_id"],
                            "class_id": track.get("class_id"),
                            "class_name": track["class_name"],
                            "confidence": track["confidence"],
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "center_x": center_x,
                            "center_y": center_y,
                            "state": track.get("state", "confirmed"),
                        }
                    )

        with tracks_jsonl.open("w", encoding="utf-8") as file:
            for frame_result in frame_results:
                file.write(json.dumps(frame_result, ensure_ascii=False))
                file.write("\n")

        summary = build_tracking_summary(frame_results)
        _write_json(summary, tracking_summary)
        return {
            "tracks_csv": tracks_csv,
            "tracks_jsonl": tracks_jsonl,
            "tracking_summary": tracking_summary,
        }

    def artifact_index(self, run_id: str) -> dict[str, str]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        return {
            name: str(relative_path)
            for name, relative_path in CORE_ARTIFACTS.items()
        }


def build_detection_summary(frame_results: list[dict[str, Any]]) -> dict[str, Any]:
    per_class_counts: dict[str, int] = {}
    total_detections = 0
    for frame_result in frame_results:
        for detection in frame_result.get("detections", []):
            class_name = str(detection["class_name"])
            per_class_counts[class_name] = per_class_counts.get(class_name, 0) + 1
            total_detections += 1
    return {
        "total_frames_processed": len(frame_results),
        "total_detections": total_detections,
        "per_class_counts": per_class_counts,
    }


def build_tracking_summary(frame_results: list[dict[str, Any]]) -> dict[str, Any]:
    per_class_track_ids: dict[str, set[int]] = {}
    track_state_counts: dict[str, int] = {}
    unique_track_ids: set[int] = set()
    total_tracks = 0
    for frame_result in frame_results:
        for track in frame_result.get("tracks", []):
            track_id = int(track["track_id"])
            class_name = str(track["class_name"])
            state = str(track.get("state", "confirmed"))
            unique_track_ids.add(track_id)
            per_class_track_ids.setdefault(class_name, set()).add(track_id)
            track_state_counts[state] = track_state_counts.get(state, 0) + 1
            total_tracks += 1
    return {
        "total_frames_processed": len(frame_results),
        "total_tracks": total_tracks,
        "unique_track_ids": len(unique_track_ids),
        "per_class_track_counts": {
            class_name: len(track_ids)
            for class_name, track_ids in sorted(per_class_track_ids.items())
        },
        "track_state_counts": track_state_counts,
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
