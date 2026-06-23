from collections.abc import Mapping, Sequence
import json
import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TRAJECTORY_ARTIFACTS = {
    "trajectory_points": "trajectory_points.csv",
    "trajectory_points_csv": "trajectory_points.csv",
    "trajectory_points_jsonl": "trajectory_points.jsonl",
    "trajectory_summary": "trajectory_summary.json",
}

EVENT_ARTIFACTS = {
    "events": "events.jsonl",
    "events_jsonl": "events.jsonl",
    "event_evidence_jsonl": "event_evidence.jsonl",
    "rule_executions_jsonl": "rule_executions.jsonl",
    "event_summary": "event_summary.json",
}

ALERT_ARTIFACTS = {
    "alerts": "alerts.jsonl",
    "alerts_jsonl": "alerts.jsonl",
    "alert_summary": "alert_summary.json",
}

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
    **TRAJECTORY_ARTIFACTS,
    "events": "events.jsonl",
    "alerts": "alerts.jsonl",
    "flow_counts": "flow_counts.json",
    "zone_statistics": "zone_statistics.json",
    "evaluation_summary": "evaluation_summary.json",
    "annotated_video": "annotated_video.mp4",
    "keyframes": "keyframes",
}

TRAJECTORY_FIELDNAMES = [
    "run_id",
    "video_id",
    "frame_index",
    "timestamp_ms",
    "track_id",
    "class_id",
    "class_name",
    "confidence",
    "state",
    "x1",
    "y1",
    "x2",
    "y2",
    "center_x",
    "center_y",
    "bottom_center_x",
    "bottom_center_y",
    "speed_px_per_frame",
    "speed_px_per_second",
    "direction_x",
    "direction_y",
    "moving_angle",
    "dwell_time_ms",
    "zone_ids_json",
    "zone_history_json",
    "lane_relation_json",
    "line_crossings_json",
    "track_length",
    "last_seen_frame",
    "last_seen_timestamp_ms",
]


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

    def write_trajectory_outputs(
        self,
        run_id: str,
        video_id: str,
        frame_results: list[dict[str, Any]],
    ) -> dict[str, Path]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        trajectory_points_csv = run_dir / "trajectory_points.csv"
        trajectory_points_jsonl = run_dir / "trajectory_points.jsonl"
        trajectory_summary = run_dir / "trajectory_summary.json"

        with trajectory_points_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=TRAJECTORY_FIELDNAMES)
            writer.writeheader()
            for frame_result in frame_results:
                for trajectory_point in frame_result.get("trajectory_points", []):
                    writer.writerow(
                        _flatten_trajectory_point(
                            run_id=run_id,
                            video_id=video_id,
                            frame_result=frame_result,
                            trajectory_point=trajectory_point,
                        )
                    )

        with trajectory_points_jsonl.open("w", encoding="utf-8") as file:
            for frame_result in frame_results:
                payload = {
                    "run_id": run_id,
                    "video_id": video_id,
                    "frame_index": frame_result.get("frame_index"),
                    "timestamp_ms": frame_result.get("timestamp_ms"),
                    "trajectory_points": frame_result.get("trajectory_points", []),
                }
                file.write(json.dumps(payload, ensure_ascii=False))
                file.write("\n")

        summary = build_trajectory_summary(
            frame_results,
            run_id=run_id,
            video_id=video_id,
        )
        _write_json(summary, trajectory_summary)
        self._merge_metadata_artifacts(run_id, TRAJECTORY_ARTIFACTS, video_id=video_id)
        return {
            "trajectory_points_csv": trajectory_points_csv,
            "trajectory_points_jsonl": trajectory_points_jsonl,
            "trajectory_summary": trajectory_summary,
        }

    def write_event_outputs(
        self,
        run_id: str,
        video_id: str,
        events: list[dict[str, Any]],
        event_evidence: list[dict[str, Any]],
        rule_executions: list[dict[str, Any]],
    ) -> dict[str, Path]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        events_jsonl = run_dir / "events.jsonl"
        event_evidence_jsonl = run_dir / "event_evidence.jsonl"
        rule_executions_jsonl = run_dir / "rule_executions.jsonl"
        event_summary = run_dir / "event_summary.json"

        _write_jsonl(events, events_jsonl)
        _write_jsonl(event_evidence, event_evidence_jsonl)
        _write_jsonl(rule_executions, rule_executions_jsonl)
        summary = build_event_summary(
            events,
            rule_executions,
            run_id=run_id,
            video_id=video_id,
        )
        _write_json(summary, event_summary)
        self._merge_metadata_artifacts(
            run_id,
            EVENT_ARTIFACTS,
            video_id=video_id,
            metadata_updates={
                "events_count": len(events),
                "event_evidence_count": len(event_evidence),
                "rule_executions_count": len(rule_executions),
            },
        )
        return {
            "events": events_jsonl,
            "events_jsonl": events_jsonl,
            "event_evidence_jsonl": event_evidence_jsonl,
            "rule_executions_jsonl": rule_executions_jsonl,
            "event_summary": event_summary,
        }

    def write_alert_outputs(
        self,
        run_id: str,
        video_id: str,
        alerts: list[dict[str, Any]],
    ) -> dict[str, Path]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        alerts_jsonl = run_dir / "alerts.jsonl"
        alert_summary = run_dir / "alert_summary.json"

        _write_jsonl(alerts, alerts_jsonl)
        _write_json(
            build_alert_summary(alerts, run_id=run_id, video_id=video_id),
            alert_summary,
        )
        self._merge_metadata_artifacts(
            run_id,
            ALERT_ARTIFACTS,
            video_id=video_id,
            metadata_updates={"alerts_count": len(alerts)},
        )
        return {
            "alerts": alerts_jsonl,
            "alerts_jsonl": alerts_jsonl,
            "alert_summary": alert_summary,
        }

    def artifact_index(self, run_id: str) -> dict[str, str]:
        _validate_run_id(run_id)
        run_dir = self.base_dir / run_id
        return {
            name: str(relative_path)
            for name, relative_path in _candidate_artifacts(run_dir).items()
            if _artifact_exists(run_dir / relative_path)
        }

    def _merge_metadata_artifacts(
        self,
        run_id: str,
        artifact_updates: dict[str, str],
        video_id: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
    ) -> Path:
        _validate_run_id(run_id)
        metadata_path = self.base_dir / run_id / "metadata.json"
        if metadata_path.is_file():
            with metadata_path.open(encoding="utf-8") as file:
                metadata = json.load(file)
        else:
            metadata = {
                "run_id": run_id,
                "created_at": _utc_now_iso(),
                "artifacts": {},
            }

        metadata.setdefault("run_id", run_id)
        if video_id is not None:
            metadata.setdefault("video_id", video_id)
        artifacts = dict(metadata.get("artifacts", {}))
        artifacts.update(artifact_updates)
        metadata["artifacts"] = artifacts
        if metadata_updates:
            metadata.update(metadata_updates)
        return _write_json(metadata, metadata_path)


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


def build_trajectory_summary(
    frame_results: list[dict[str, Any]],
    run_id: str | None = None,
    video_id: str | None = None,
) -> dict[str, Any]:
    per_class_track_ids: dict[str, set[Any]] = {}
    track_state_counts: dict[str, int] = {}
    unique_track_ids: set[Any] = set()
    max_track_lengths: dict[Any, int] = {}
    speeds_px_per_second: list[float] = []
    zone_counts: dict[str, int] = {}
    line_crossing_counts: dict[str, int] = {}
    total_trajectory_points = 0

    for frame_result in frame_results:
        for trajectory_point in frame_result.get("trajectory_points", []):
            total_trajectory_points += 1
            track_id = trajectory_point.get("track_id")
            class_name = str(trajectory_point.get("class_name", ""))
            state = str(trajectory_point.get("state", "confirmed"))

            if track_id is not None:
                unique_track_ids.add(track_id)
                per_class_track_ids.setdefault(class_name, set()).add(track_id)
                track_length = trajectory_point.get("track_length")
                if track_length is not None:
                    max_track_lengths[track_id] = max(
                        int(track_length),
                        max_track_lengths.get(track_id, 0),
                    )

            track_state_counts[state] = track_state_counts.get(state, 0) + 1

            speed_px_per_second = trajectory_point.get("speed_px_per_second")
            if speed_px_per_second is not None:
                speeds_px_per_second.append(float(speed_px_per_second))

            for zone_id in trajectory_point.get("zone_ids", []) or []:
                zone_key = str(zone_id)
                zone_counts[zone_key] = zone_counts.get(zone_key, 0) + 1

            for crossing in trajectory_point.get("line_crossings", []) or []:
                crossing_key = _line_crossing_key(crossing)
                if crossing_key is None:
                    continue
                line_crossing_counts[crossing_key] = (
                    line_crossing_counts.get(crossing_key, 0) + 1
                )

    track_lengths = list(max_track_lengths.values())
    return {
        "run_id": run_id,
        "video_id": video_id,
        "total_frames_processed": len(frame_results),
        "total_trajectory_points": total_trajectory_points,
        "unique_track_ids": len(unique_track_ids),
        "per_class_track_counts": {
            class_name: len(track_ids)
            for class_name, track_ids in sorted(per_class_track_ids.items())
        },
        "track_state_counts": dict(sorted(track_state_counts.items())),
        "avg_track_length": (
            round(sum(track_lengths) / len(track_lengths), 6) if track_lengths else 0.0
        ),
        "max_track_length": max(track_lengths) if track_lengths else 0,
        "speed_unit": "px_per_second",
        "avg_speed_px_per_second": (
            round(sum(speeds_px_per_second) / len(speeds_px_per_second), 6)
            if speeds_px_per_second
            else None
        ),
        "zone_counts": dict(sorted(zone_counts.items())),
        "line_crossing_counts": dict(sorted(line_crossing_counts.items())),
    }


def build_event_summary(
    events: list[dict[str, Any]],
    rule_executions: list[dict[str, Any]],
    run_id: str | None = None,
    video_id: str | None = None,
) -> dict[str, Any]:
    per_event_type_counts: dict[str, int] = {}
    per_severity_counts: dict[str, int] = {}
    per_status_counts: dict[str, int] = {}
    unique_track_ids: set[Any] = set()
    rule_execution_counts: dict[str, int] = {}
    event_times: list[int] = []

    for event in events:
        event_type = event.get("event_type")
        if event_type is not None:
            event_type_key = str(event_type)
            per_event_type_counts[event_type_key] = (
                per_event_type_counts.get(event_type_key, 0) + 1
            )

        severity = event.get("severity")
        if severity is not None:
            severity_key = str(severity)
            per_severity_counts[severity_key] = (
                per_severity_counts.get(severity_key, 0) + 1
            )

        status = event.get("status")
        if status is not None:
            status_key = str(status)
            per_status_counts[status_key] = per_status_counts.get(status_key, 0) + 1

        track_id = event.get("track_id")
        if track_id is not None:
            unique_track_ids.add(track_id)

        for time_key in ("start_time_ms", "end_time_ms"):
            timestamp_ms = event.get(time_key)
            if timestamp_ms is not None:
                event_times.append(int(timestamp_ms))

    for rule_execution in rule_executions:
        status = rule_execution.get("status")
        if status is None:
            continue
        status_key = str(status)
        rule_execution_counts[status_key] = (
            rule_execution_counts.get(status_key, 0) + 1
        )

    return {
        "run_id": run_id,
        "video_id": video_id,
        "total_events": len(events),
        "per_event_type_counts": dict(sorted(per_event_type_counts.items())),
        "per_severity_counts": dict(sorted(per_severity_counts.items())),
        "per_status_counts": dict(sorted(per_status_counts.items())),
        "unique_track_ids": len(unique_track_ids),
        "rule_execution_counts": dict(sorted(rule_execution_counts.items())),
        "first_event_time_ms": min(event_times) if event_times else None,
        "last_event_time_ms": max(event_times) if event_times else None,
    }


def build_alert_summary(
    alerts: list[dict[str, Any]],
    run_id: str | None = None,
    video_id: str | None = None,
) -> dict[str, Any]:
    per_alert_type_counts: dict[str, int] = {}
    per_level_counts: dict[str, int] = {}
    per_status_counts: dict[str, int] = {}
    unique_event_ids: set[Any] = set()
    unique_track_ids: set[Any] = set()
    alert_times: list[int] = []

    for alert in alerts:
        alert_type = alert.get("alert_type")
        if alert_type is not None:
            alert_type_key = str(alert_type)
            per_alert_type_counts[alert_type_key] = (
                per_alert_type_counts.get(alert_type_key, 0) + 1
            )

        level = alert.get("level")
        if level is not None:
            level_key = str(level)
            per_level_counts[level_key] = per_level_counts.get(level_key, 0) + 1

        status = alert.get("status")
        if status is not None:
            status_key = str(status)
            per_status_counts[status_key] = per_status_counts.get(status_key, 0) + 1

        event_id = alert.get("event_id")
        if event_id is not None:
            unique_event_ids.add(event_id)

        track_id = alert.get("track_id")
        if track_id is not None:
            unique_track_ids.add(track_id)

        timestamp_ms = alert.get("timestamp_ms")
        if timestamp_ms is not None:
            alert_times.append(int(timestamp_ms))

    return {
        "run_id": run_id,
        "video_id": video_id,
        "total_alerts": len(alerts),
        "per_alert_type_counts": dict(sorted(per_alert_type_counts.items())),
        "per_level_counts": dict(sorted(per_level_counts.items())),
        "per_status_counts": dict(sorted(per_status_counts.items())),
        "unique_event_ids": len(unique_event_ids),
        "unique_track_ids": len(unique_track_ids),
        "first_alert_time_ms": min(alert_times) if alert_times else None,
        "last_alert_time_ms": max(alert_times) if alert_times else None,
    }


def _flatten_trajectory_point(
    run_id: str,
    video_id: str,
    frame_result: dict[str, Any],
    trajectory_point: dict[str, Any],
) -> dict[str, Any]:
    x1, y1, x2, y2 = _sequence_values(trajectory_point.get("bbox"), 4)
    center_x, center_y = _sequence_values(trajectory_point.get("center"), 2)
    bottom_center_x, bottom_center_y = _sequence_values(
        trajectory_point.get("bottom_center"),
        2,
    )
    direction_x, direction_y = _sequence_values(
        trajectory_point.get("direction_vector"),
        2,
    )
    return {
        "run_id": run_id,
        "video_id": video_id,
        "frame_index": _csv_value(frame_result.get("frame_index")),
        "timestamp_ms": _csv_value(frame_result.get("timestamp_ms")),
        "track_id": _csv_value(trajectory_point.get("track_id")),
        "class_id": _csv_value(trajectory_point.get("class_id")),
        "class_name": _csv_value(trajectory_point.get("class_name")),
        "confidence": _csv_value(trajectory_point.get("confidence")),
        "state": _csv_value(trajectory_point.get("state")),
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "center_x": center_x,
        "center_y": center_y,
        "bottom_center_x": bottom_center_x,
        "bottom_center_y": bottom_center_y,
        "speed_px_per_frame": _csv_value(
            trajectory_point.get("speed_px_per_frame")
        ),
        "speed_px_per_second": _csv_value(
            trajectory_point.get("speed_px_per_second")
        ),
        "direction_x": direction_x,
        "direction_y": direction_y,
        "moving_angle": _csv_value(trajectory_point.get("moving_angle")),
        "dwell_time_ms": _csv_value(trajectory_point.get("dwell_time_ms")),
        "zone_ids_json": _json_csv_value(trajectory_point, "zone_ids"),
        "zone_history_json": _json_csv_value(trajectory_point, "zone_history"),
        "lane_relation_json": _json_csv_value(trajectory_point, "lane_relation"),
        "line_crossings_json": _json_csv_value(trajectory_point, "line_crossings"),
        "track_length": _csv_value(trajectory_point.get("track_length")),
        "last_seen_frame": _csv_value(trajectory_point.get("last_seen_frame")),
        "last_seen_timestamp_ms": _csv_value(
            trajectory_point.get("last_seen_timestamp_ms")
        ),
    }


def _sequence_values(value: Any, length: int) -> tuple[Any, ...]:
    if value is None or isinstance(value, str | bytes):
        return ("",) * length
    if not isinstance(value, Sequence) or len(value) < length:
        return ("",) * length
    return tuple(_csv_value(value[index]) for index in range(length))


def _json_csv_value(payload: Mapping[str, Any], key: str) -> str:
    if key not in payload or payload[key] is None:
        return ""
    return json.dumps(payload[key], ensure_ascii=False, sort_keys=True)


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def _line_crossing_key(crossing: Any) -> str | None:
    if isinstance(crossing, Mapping):
        crossing_id = (
            crossing.get("line_id")
            or crossing.get("line_name")
            or crossing.get("id")
        )
        if crossing_id is None:
            return None
        return str(crossing_id)
    if crossing is None:
        return None
    return str(crossing)


def _write_json(data: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False))
            file.write("\n")
    return output_path


def _candidate_artifacts(run_dir: Path) -> dict[str, str]:
    metadata_path = run_dir / "metadata.json"
    if metadata_path.is_file():
        with metadata_path.open(encoding="utf-8") as file:
            metadata = json.load(file)
        artifacts = metadata.get("artifacts")
        if isinstance(artifacts, dict):
            return {str(name): str(path) for name, path in artifacts.items()}
    return dict(CORE_ARTIFACTS)


def _artifact_exists(path: Path) -> bool:
    if path.is_file():
        return True
    return path.is_dir() and any(path.iterdir())


def _validate_run_id(run_id: str) -> None:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be a safe directory name")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
