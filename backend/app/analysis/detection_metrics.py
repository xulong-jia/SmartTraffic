from collections.abc import Mapping, Sequence
from typing import Any


def bbox_iou(box_a: Sequence[float | int], box_b: Sequence[float | int]) -> float:
    a = _coerce_bbox(box_a)
    b = _coerce_bbox(box_b)
    if a is None or b is None:
        return 0.0
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_width = max(0.0, inter_x2 - inter_x1)
    inter_height = max(0.0, inter_y2 - inter_y1)
    intersection = inter_width * inter_height
    if intersection <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - intersection
    if union <= 0:
        return 0.0
    return _round_metric(intersection / union)


def compute_detection_benchmark(
    predictions: Any,
    ground_truth: Any,
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    predicted_boxes = normalize_detection_records(predictions, source="prediction")
    gt_boxes = normalize_detection_records(ground_truth, source="ground_truth")
    if not gt_boxes:
        return {
            "status": "insufficient_data",
            "reason": "not_enough_annotations",
            "iou_threshold": iou_threshold,
            "overall": {
                "mAP": None,
                "precision": None,
                "recall": None,
                "true_positive": 0,
                "false_positive": len(predicted_boxes),
                "false_negative": 0,
            },
            "per_class": {},
            "false_positives": predicted_boxes,
            "false_negatives": [],
        }

    per_class: dict[str, dict[str, Any]] = {}
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    aps: list[float] = []

    classes = sorted({record["class_name"] for record in gt_boxes})
    for class_name in classes:
        class_gt = [record for record in gt_boxes if record["class_name"] == class_name]
        class_predictions = sorted(
            [record for record in predicted_boxes if record["class_name"] == class_name],
            key=lambda item: float(item.get("confidence", 0.0)),
            reverse=True,
        )
        matched_gt: set[int] = set()
        tp_flags: list[int] = []
        fp_flags: list[int] = []
        for prediction in class_predictions:
            match_index = _best_gt_match(
                prediction,
                class_gt,
                matched_gt=matched_gt,
                iou_threshold=iou_threshold,
            )
            if match_index is None:
                fp_flags.append(1)
                tp_flags.append(0)
                false_positives.append(prediction)
                continue
            matched_gt.add(match_index)
            tp_flags.append(1)
            fp_flags.append(0)

        class_tp = sum(tp_flags)
        class_fp = sum(fp_flags)
        class_fn = len(class_gt) - class_tp
        for index, gt_record in enumerate(class_gt):
            if index not in matched_gt:
                false_negatives.append(gt_record)
        precision = _ratio_or_zero(class_tp, class_tp + class_fp)
        recall = _ratio_or_zero(class_tp, class_tp + class_fn)
        ap = _average_precision(tp_flags, fp_flags, len(class_gt))
        aps.append(ap)
        per_class[class_name] = {
            "true_positive": class_tp,
            "false_positive": class_fp,
            "false_negative": class_fn,
            "precision": precision,
            "recall": recall,
            "ap": ap,
            "ground_truth_count": len(class_gt),
            "prediction_count": len(class_predictions),
        }
        total_tp += class_tp
        total_fp += class_fp
        total_fn += class_fn

    # Predictions for classes absent from GT are false positives but do not enter mAP.
    gt_classes = set(classes)
    for prediction in predicted_boxes:
        if prediction["class_name"] not in gt_classes:
            total_fp += 1
            false_positives.append(prediction)

    return {
        "status": "available",
        "reason": None,
        "iou_threshold": iou_threshold,
        "overall": {
            "mAP": _round_metric(sum(aps) / len(aps)) if aps else 0.0,
            "precision": _ratio_or_zero(total_tp, total_tp + total_fp),
            "recall": _ratio_or_zero(total_tp, total_tp + total_fn),
            "true_positive": total_tp,
            "false_positive": total_fp,
            "false_negative": total_fn,
            "ground_truth_count": len(gt_boxes),
            "prediction_count": len(predicted_boxes),
        },
        "per_class": per_class,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def normalize_detection_records(payload: Any, *, source: str) -> list[dict[str, Any]]:
    rows = _payload_rows(payload, preferred_keys=("detections", "annotations", "ground_truth", "objects", "records"))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        frame_index = _optional_int(row.get("frame_index"))
        nested = _first_list(row, ("detections", "annotations", "ground_truth", "objects"))
        if nested is not None:
            for item in nested:
                if isinstance(item, Mapping):
                    record = _normalize_detection(item, source=source, frame_index=frame_index)
                    if record is not None:
                        normalized.append(record)
            continue
        record = _normalize_detection(row, source=source, frame_index=frame_index)
        if record is not None:
            normalized.append(record)
    return normalized


def _normalize_detection(
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
    return {
        "frame_index": _optional_int(payload.get("frame_index")) if payload.get("frame_index") is not None else frame_index,
        "class_name": str(class_name),
        "confidence": float(payload.get("confidence", 1.0) or 0.0),
        "bbox": bbox,
        "source": source,
    }


def _best_gt_match(
    prediction: Mapping[str, Any],
    ground_truth: list[dict[str, Any]],
    *,
    matched_gt: set[int],
    iou_threshold: float,
) -> int | None:
    best_index: int | None = None
    best_iou = 0.0
    for index, gt_record in enumerate(ground_truth):
        if index in matched_gt:
            continue
        if gt_record.get("frame_index") != prediction.get("frame_index"):
            continue
        iou = bbox_iou(prediction["bbox"], gt_record["bbox"])
        if iou >= iou_threshold and iou > best_iou:
            best_index = index
            best_iou = iou
    return best_index


def _average_precision(tp_flags: list[int], fp_flags: list[int], gt_count: int) -> float:
    if gt_count <= 0:
        return 0.0
    if not tp_flags:
        return 0.0
    cumulative_tp = 0
    cumulative_fp = 0
    recalls = [0.0]
    precisions = [1.0]
    for tp, fp in zip(tp_flags, fp_flags, strict=True):
        cumulative_tp += tp
        cumulative_fp += fp
        recalls.append(cumulative_tp / gt_count)
        precisions.append(cumulative_tp / max(cumulative_tp + cumulative_fp, 1))
    recalls.append(1.0)
    precisions.append(0.0)
    for index in range(len(precisions) - 2, -1, -1):
        precisions[index] = max(precisions[index], precisions[index + 1])
    ap = 0.0
    for index in range(1, len(recalls)):
        if recalls[index] != recalls[index - 1]:
            ap += (recalls[index] - recalls[index - 1]) * precisions[index]
    return _round_metric(ap)


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
