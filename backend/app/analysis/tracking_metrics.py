from collections.abc import Mapping, Sequence
from typing import Any

from app.analysis.detection_metrics import bbox_iou


def compute_tracking_benchmark(
    predictions: Any,
    ground_truth: Any,
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    predicted_tracks = normalize_tracking_records(predictions, source="prediction")
    gt_tracks = normalize_tracking_records(ground_truth, source="ground_truth")
    if not gt_tracks:
        return {
            "status": "insufficient_data",
            "reason": "not_enough_annotations",
            "iou_threshold": iou_threshold,
            "frame_count": _frame_count(predicted_tracks, gt_tracks),
            "gt_count": 0,
            "predicted_count": len(predicted_tracks),
            "idtp": 0,
            "idfp": len(predicted_tracks),
            "idfn": 0,
            "idf1": None,
            "mota": None,
            "false_positive_count": len(predicted_tracks),
            "false_negative_count": 0,
            "id_switch_count": 0,
            "track_lost_count": 0,
            "switch_details": [],
            "lost_track_details": [],
        }

    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unmatched_predictions: list[dict[str, Any]] = []
    unmatched_gt: list[dict[str, Any]] = []
    last_prediction_by_gt: dict[str, str] = {}
    switch_details: list[dict[str, Any]] = []

    for frame_index in sorted({record.get("frame_index") for record in predicted_tracks + gt_tracks}):
        frame_predictions = [record for record in predicted_tracks if record.get("frame_index") == frame_index]
        frame_gt = [record for record in gt_tracks if record.get("frame_index") == frame_index]
        frame_matches = _associate_frame(
            frame_predictions,
            frame_gt,
            iou_threshold=iou_threshold,
        )
        matched_prediction_indices = {prediction_index for prediction_index, _ in frame_matches}
        matched_gt_indices = {gt_index for _, gt_index in frame_matches}
        for prediction_index, gt_index in frame_matches:
            prediction = frame_predictions[prediction_index]
            gt_record = frame_gt[gt_index]
            matches.append((prediction, gt_record))
            gt_track_id = str(gt_record["gt_track_id"])
            predicted_track_id = str(prediction["track_id"])
            previous_track_id = last_prediction_by_gt.get(gt_track_id)
            if previous_track_id is not None and previous_track_id != predicted_track_id:
                switch_details.append(
                    {
                        "frame_index": frame_index,
                        "gt_track_id": gt_track_id,
                        "previous_track_id": previous_track_id,
                        "new_track_id": predicted_track_id,
                    }
                )
            last_prediction_by_gt[gt_track_id] = predicted_track_id
        unmatched_predictions.extend(
            prediction
            for index, prediction in enumerate(frame_predictions)
            if index not in matched_prediction_indices
        )
        unmatched_gt.extend(
            gt_record
            for index, gt_record in enumerate(frame_gt)
            if index not in matched_gt_indices
        )

    false_positive_count = len(unmatched_predictions)
    false_negative_count = len(unmatched_gt)
    id_switch_count = len(switch_details)
    idtp = len(matches)
    idfp = false_positive_count
    idfn = false_negative_count
    idf1 = _ratio_or_zero(2 * idtp, (2 * idtp) + idfp + idfn)
    mota = _round_metric(1 - ((false_negative_count + false_positive_count + id_switch_count) / len(gt_tracks)))
    lost_track_details = _lost_track_segments(unmatched_gt)
    return {
        "status": "available",
        "reason": None,
        "iou_threshold": iou_threshold,
        "frame_count": _frame_count(predicted_tracks, gt_tracks),
        "gt_count": len(gt_tracks),
        "predicted_count": len(predicted_tracks),
        "idtp": idtp,
        "idfp": idfp,
        "idfn": idfn,
        "idf1": idf1,
        "mota": mota,
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "id_switch_count": id_switch_count,
        "track_lost_count": len(lost_track_details),
        "switch_details": switch_details,
        "lost_track_details": lost_track_details,
    }


def normalize_tracking_records(payload: Any, *, source: str) -> list[dict[str, Any]]:
    rows = _payload_rows(payload, preferred_keys=("tracks", "annotations", "ground_truth", "records"))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        frame_index = _optional_int(row.get("frame_index"))
        nested = _first_list(row, ("tracks", "annotations", "ground_truth", "objects"))
        if nested is not None:
            for item in nested:
                if isinstance(item, Mapping):
                    record = _normalize_track(item, source=source, frame_index=frame_index)
                    if record is not None:
                        normalized.append(record)
            continue
        record = _normalize_track(row, source=source, frame_index=frame_index)
        if record is not None:
            normalized.append(record)
    return normalized


def _normalize_track(
    payload: Mapping[str, Any],
    *,
    source: str,
    frame_index: int | None,
) -> dict[str, Any] | None:
    bbox = _coerce_bbox(payload.get("bbox"))
    if bbox is None:
        return None
    class_name = payload.get("class_name") or payload.get("label") or payload.get("category")
    if class_name is None:
        return None
    track_id = payload.get("track_id")
    gt_track_id = payload.get("gt_track_id", track_id)
    if source == "prediction" and track_id is None:
        return None
    if source == "ground_truth" and gt_track_id is None:
        return None
    return {
        "frame_index": _optional_int(payload.get("frame_index")) if payload.get("frame_index") is not None else frame_index,
        "class_name": str(class_name),
        "track_id": str(track_id) if track_id is not None else str(gt_track_id),
        "gt_track_id": str(gt_track_id),
        "bbox": bbox,
        "source": source,
    }


def _associate_frame(
    predictions: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    *,
    iou_threshold: float,
) -> list[tuple[int, int]]:
    candidates: list[tuple[float, int, int]] = []
    for prediction_index, prediction in enumerate(predictions):
        for gt_index, gt_record in enumerate(ground_truth):
            if prediction["class_name"] != gt_record["class_name"]:
                continue
            iou = bbox_iou(prediction["bbox"], gt_record["bbox"])
            if iou >= iou_threshold:
                candidates.append((iou, prediction_index, gt_index))
    candidates.sort(reverse=True)
    matched_predictions: set[int] = set()
    matched_gt: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, prediction_index, gt_index in candidates:
        if prediction_index in matched_predictions or gt_index in matched_gt:
            continue
        matched_predictions.add(prediction_index)
        matched_gt.add(gt_index)
        matches.append((prediction_index, gt_index))
    return matches


def _lost_track_segments(unmatched_gt: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_track: dict[str, list[int]] = {}
    for record in unmatched_gt:
        frame_index = record.get("frame_index")
        if frame_index is None:
            continue
        by_track.setdefault(str(record["gt_track_id"]), []).append(int(frame_index))
    details: list[dict[str, Any]] = []
    for gt_track_id, frames in sorted(by_track.items()):
        sorted_frames = sorted(set(frames))
        start = previous = sorted_frames[0]
        for frame_index in sorted_frames[1:]:
            if frame_index == previous + 1:
                previous = frame_index
                continue
            details.append({"gt_track_id": gt_track_id, "start_frame": start, "end_frame": previous})
            start = previous = frame_index
        details.append({"gt_track_id": gt_track_id, "start_frame": start, "end_frame": previous})
    return details


def _frame_count(predictions: list[dict[str, Any]], ground_truth: list[dict[str, Any]]) -> int:
    return len({record.get("frame_index") for record in predictions + ground_truth if record.get("frame_index") is not None})


def _payload_rows(payload: Any, *, preferred_keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, Mapping):
        for key in preferred_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        frames = payload.get("frames")
        if isinstance(frames, list):
            return [item for item in frames if isinstance(item, Mapping)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    return []


def _first_list(payload: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any] | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return None


def _coerce_bbox(value: Any) -> list[float] | None:
    if isinstance(value, Mapping):
        keys = ("x1", "y1", "x2", "y2")
        if not all(key in value for key in keys):
            return None
        raw = [value[key] for key in keys]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4:
        raw = list(value)
    else:
        return None
    try:
        x1, y1, x2, y2 = [float(item) for item in raw]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ratio_or_zero(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return _round_metric(float(numerator) / float(denominator))


def _round_metric(value: float) -> float:
    return round(float(value), 6)
