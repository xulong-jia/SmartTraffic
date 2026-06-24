from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from app.cv.video_writer import AnnotatedVideoWriter, draw_detections, draw_tracks


STAGE6F_SCHEMA_VERSION = "stage6f.v1"


def build_visual_artifacts(
    *,
    run_id: str,
    run_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    try:
        keyframe_result = _write_keyframes(
            run_id=run_id,
            run_dir=run_dir,
            metadata=metadata,
        )
    except Exception:
        keyframe_result = _write_keyframe_error_index(
            run_id=run_id,
            run_dir=run_dir,
            metadata=metadata,
        )
    try:
        annotated_video_result = _write_annotated_video(
            run_dir=run_dir,
            metadata=metadata,
        )
    except Exception:
        annotated_video_result = {
            "status": "error",
            "path": "annotated_video.mp4",
            "record_count": 0,
        }
    return {
        "keyframes": {
            "status": keyframe_result["status"],
            "path": "keyframes/",
            "record_count": len(keyframe_result["items"]),
        },
        "keyframes_index": {
            "status": "available",
            "path": "keyframes/index.json",
            "record_count": 1,
        },
        "annotated_video": annotated_video_result,
    }


def _write_keyframes(
    *,
    run_id: str,
    run_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    keyframes_dir = run_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    events = _read_jsonl(_artifact_path(run_dir, metadata, "events_jsonl", "events.jsonl"))
    event_evidence = _read_jsonl(
        _artifact_path(run_dir, metadata, "event_evidence_jsonl", "event_evidence.jsonl")
    )
    alerts = _read_jsonl(_artifact_path(run_dir, metadata, "alerts_jsonl", "alerts.jsonl"))
    evidence_by_event_id = _first_by_key(event_evidence, "event_id")
    requests = [
        *_event_keyframe_requests(events, evidence_by_event_id),
        *_alert_keyframe_requests(alerts),
    ]
    source_video = _resolve_source_video(run_dir, metadata)
    detections_by_frame = _frames_by_index(
        _read_jsonl(_artifact_path(run_dir, metadata, "detections_jsonl", "detections.jsonl")),
        "detections",
    )
    tracks_by_frame = _frames_by_index(
        _read_jsonl(_artifact_path(run_dir, metadata, "tracks_jsonl", "tracks.jsonl")),
        "tracks",
    )

    if not requests:
        items: list[dict[str, Any]] = []
        status = "empty"
    elif source_video is None:
        items = [
            {
                **request,
                "status": "missing_source_video",
            }
            for request in requests
        ]
        status = "missing_source_video"
    else:
        items = _capture_keyframes(
            source_video=source_video,
            requests=requests,
            run_dir=run_dir,
            detections_by_frame=detections_by_frame,
            tracks_by_frame=tracks_by_frame,
        )
        status = _aggregate_item_status(items)

    index_payload = {
        "schema_version": STAGE6F_SCHEMA_VERSION,
        "run_id": run_id,
        "video_id": str(metadata.get("video_id", "")),
        "generated_at": _utc_now_iso(),
        "status": status,
        "items": items,
    }
    _write_json(index_payload, keyframes_dir / "index.json")
    return {"status": status, "items": items}


def _write_keyframe_error_index(
    *,
    run_id: str,
    run_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    keyframes_dir = run_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        {
            "schema_version": STAGE6F_SCHEMA_VERSION,
            "run_id": run_id,
            "video_id": str(metadata.get("video_id", "")),
            "generated_at": _utc_now_iso(),
            "status": "error",
            "items": [],
        },
        keyframes_dir / "index.json",
    )
    return {"status": "error", "items": []}


def _write_annotated_video(
    *,
    run_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    output_path = run_dir / "annotated_video.mp4"
    source_video = _resolve_source_video(run_dir, metadata)
    if source_video is None:
        output_path.unlink(missing_ok=True)
        return {
            "status": "missing_source_video",
            "path": "annotated_video.mp4",
            "record_count": 0,
        }

    capture = None
    try:
        cv2 = _import_cv2()
        capture = cv2.VideoCapture(str(source_video))
        if not capture.isOpened():
            output_path.unlink(missing_ok=True)
            return {
                "status": "error",
                "path": "annotated_video.mp4",
                "record_count": 0,
            }
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if fps <= 0:
            fps = float(_metadata_value(metadata, "fps", default=1.0) or 1.0)
        if width <= 0 or height <= 0:
            width = int(_metadata_value(metadata, "width", default=0) or 0)
            height = int(_metadata_value(metadata, "height", default=0) or 0)
        if width <= 0 or height <= 0:
            output_path.unlink(missing_ok=True)
            return {
                "status": "error",
                "path": "annotated_video.mp4",
                "record_count": 0,
            }

        detections_by_frame = _frames_by_index(
            _read_jsonl(
                _artifact_path(run_dir, metadata, "detections_jsonl", "detections.jsonl")
            ),
            "detections",
        )
        tracks_by_frame = _frames_by_index(
            _read_jsonl(_artifact_path(run_dir, metadata, "tracks_jsonl", "tracks.jsonl")),
            "tracks",
        )
        events_by_frame = _events_by_frame(
            _read_jsonl(_artifact_path(run_dir, metadata, "events_jsonl", "events.jsonl"))
        )

        written_frames = 0
        with AnnotatedVideoWriter(
            output_path,
            fps=fps,
            frame_size=(width, height),
        ) as writer:
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame = _annotate_frame(
                    frame=frame,
                    frame_index=frame_index,
                    detections=detections_by_frame.get(frame_index, []),
                    tracks=tracks_by_frame.get(frame_index, []),
                    events=events_by_frame.get(frame_index, []),
                )
                writer.write_frame(frame)
                written_frames += 1
                frame_index += 1
    except (OSError, RuntimeError, ValueError):
        output_path.unlink(missing_ok=True)
        return {
            "status": "error",
            "path": "annotated_video.mp4",
            "record_count": 0,
        }
    finally:
        if capture is not None:
            capture.release()

    if written_frames == 0 or not output_path.is_file():
        output_path.unlink(missing_ok=True)
        return {
            "status": "empty",
            "path": "annotated_video.mp4",
            "record_count": 0,
        }
    return {
        "status": "available",
        "path": "annotated_video.mp4",
        "record_count": 1,
    }


def _event_keyframe_requests(
    events: list[dict[str, Any]],
    evidence_by_event_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        event_id = _string_or_none(event.get("event_id")) or f"event_{index}"
        evidence = evidence_by_event_id.get(event_id, {})
        frame_index = _first_int(
            event.get("frame_index"),
            event.get("end_frame"),
            event.get("start_frame"),
            evidence.get("frame_index"),
            default=None,
        )
        if frame_index is None:
            continue
        timestamp_ms = _first_int(
            event.get("timestamp_ms"),
            event.get("end_time_ms"),
            event.get("start_time_ms"),
            evidence.get("timestamp_ms"),
            default=None,
        )
        keyframe_id = f"event_{_safe_filename(event_id)}_{frame_index}"
        requests.append(
            {
                "keyframe_id": keyframe_id,
                "source_type": "event",
                "source_id": event_id,
                "event_id": event_id,
                "alert_id": None,
                "frame_index": frame_index,
                "timestamp_ms": timestamp_ms,
                "path": f"keyframes/{keyframe_id}.jpg",
            }
        )
    return requests


def _alert_keyframe_requests(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index, alert in enumerate(alerts):
        alert_id = _string_or_none(alert.get("alert_id") or alert.get("id")) or f"alert_{index}"
        frame_index = _first_int(alert.get("frame_index"), default=None)
        if frame_index is None:
            continue
        event_id = _string_or_none(alert.get("event_id"))
        timestamp_ms = _first_int(alert.get("timestamp_ms"), default=None)
        keyframe_id = f"alert_{_safe_filename(alert_id)}_{frame_index}"
        requests.append(
            {
                "keyframe_id": keyframe_id,
                "source_type": "alert",
                "source_id": alert_id,
                "event_id": event_id,
                "alert_id": alert_id,
                "frame_index": frame_index,
                "timestamp_ms": timestamp_ms,
                "path": f"keyframes/{keyframe_id}.jpg",
            }
        )
    return requests


def _capture_keyframes(
    *,
    source_video: Path,
    requests: list[dict[str, Any]],
    run_dir: Path,
    detections_by_frame: dict[int, list[dict[str, Any]]],
    tracks_by_frame: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    capture = None
    try:
        cv2 = _import_cv2()
        capture = cv2.VideoCapture(str(source_video))
        if not capture.isOpened():
            return [{**request, "status": "error"} for request in requests]
        items: list[dict[str, Any]] = []
        for request in requests:
            frame_index = int(request["frame_index"])
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                items.append({**request, "status": "error"})
                continue
            frame = _annotate_frame(
                frame=frame,
                frame_index=frame_index,
                detections=detections_by_frame.get(frame_index, []),
                tracks=tracks_by_frame.get(frame_index, []),
                events=[request],
            )
            output_path = run_dir / str(request["path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if cv2.imwrite(str(output_path), frame):
                items.append({**request, "status": "available"})
            else:
                items.append({**request, "status": "error"})
        return items
    except (OSError, RuntimeError, ValueError):
        return [{**request, "status": "error"} for request in requests]
    finally:
        if capture is not None:
            capture.release()


def _annotate_frame(
    *,
    frame: Any,
    frame_index: int,
    detections: list[dict[str, Any]],
    tracks: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> Any:
    cv2 = _import_cv2()
    output = draw_detections(frame, detections) if detections else frame.copy()
    output = draw_tracks(output, tracks) if tracks else output
    labels = [_event_label(event) for event in events]
    if labels:
        text = f"frame {frame_index} | " + " | ".join(labels[:3])
        cv2.putText(
            output,
            text[:100],
            (8, 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 220, 255),
            1,
            cv2.LINE_AA,
        )
    return output


def _event_label(event: dict[str, Any]) -> str:
    source_type = event.get("source_type")
    if source_type:
        return f"{source_type}:{event.get('source_id')}"
    event_type = event.get("event_type")
    event_id = event.get("event_id")
    return str(event_type or event_id or "event")


def _resolve_source_video(run_dir: Path, metadata: dict[str, Any]) -> Path | None:
    from app.core.config import get_settings

    candidates: list[Path] = []
    video_metadata = metadata.get("video_metadata")
    if isinstance(video_metadata, dict) and video_metadata.get("video_path"):
        candidates.append(Path(str(video_metadata["video_path"])))
    if metadata.get("input_video"):
        input_video = Path(str(metadata["input_video"]))
        candidates.append(input_video)
        if not input_video.is_absolute():
            settings = get_settings()
            candidates.append(settings.local_videos_dir / input_video)
            candidates.append(run_dir / input_video)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _frames_by_index(rows: list[dict[str, Any]], key: str) -> dict[int, list[dict[str, Any]]]:
    indexed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        frame_index = _first_int(row.get("frame_index"), default=None)
        if frame_index is None:
            continue
        values = row.get(key)
        if isinstance(values, list):
            indexed[frame_index] = values
    return indexed


def _events_by_frame(events: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    indexed: dict[int, list[dict[str, Any]]] = {}
    for event in events:
        frame_index = _first_int(
            event.get("frame_index"),
            event.get("end_frame"),
            event.get("start_frame"),
            default=None,
        )
        if frame_index is None:
            continue
        indexed.setdefault(frame_index, []).append(event)
    return indexed


def _artifact_path(
    run_dir: Path,
    metadata: dict[str, Any],
    key: str,
    default: str,
) -> Path:
    artifacts = metadata.get("artifacts")
    if isinstance(artifacts, dict) and artifacts.get(key):
        return run_dir / str(artifacts[key])
    return run_dir / default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _first_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        indexed.setdefault(str(value), row)
    return indexed


def _aggregate_item_status(items: list[dict[str, Any]]) -> str:
    if not items:
        return "empty"
    statuses = {str(item.get("status", "")) for item in items}
    if statuses == {"available"}:
        return "available"
    if statuses == {"missing_source_video"}:
        return "missing_source_video"
    return "error"


def _metadata_value(metadata: dict[str, Any], key: str, *, default: Any) -> Any:
    video_metadata = metadata.get("video_metadata")
    if isinstance(video_metadata, dict) and video_metadata.get(key) is not None:
        return video_metadata[key]
    return default


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "item"


def _first_int(*values: Any, default: int | None) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _string_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return path


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to write visual artifacts") from exc
    return cv2
