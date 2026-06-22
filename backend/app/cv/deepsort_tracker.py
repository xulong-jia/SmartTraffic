from dataclasses import dataclass
from typing import Any


@dataclass
class _TrackState:
    track_id: int
    class_name: str
    class_id: int | None
    confidence: float
    bbox: list[float]
    hits: int = 1
    missed: int = 0


class DeepSortTracker:
    """DeepSORT adapter with deterministic dry-run tracking fallback."""

    def __init__(
        self,
        dry_run: bool = True,
        max_age: int = 30,
        n_init: int = 1,
        max_iou_distance: float = 0.7,
        max_cosine_distance: float = 0.2,
        target_classes: set[str] | list[str] | tuple[str, ...] | None = None,
        min_confidence: float = 0.0,
    ) -> None:
        self.dry_run = dry_run
        self.max_age = max(0, int(max_age))
        self.n_init = max(1, int(n_init))
        self.max_iou_distance = float(max_iou_distance)
        self.max_cosine_distance = float(max_cosine_distance)
        self.target_classes = set(target_classes) if target_classes else None
        self.min_confidence = float(min_confidence)
        self._tracks: dict[int, _TrackState] = {}
        self._next_track_id = 1
        self._real_tracker: Any | None = None
        self._fallback_reason: str | None = None
        self._class_ids_by_name: dict[str, int | None] = {}

        if not self.dry_run:
            self._real_tracker = self._load_real_tracker()
            if self._real_tracker is None:
                self._fallback_reason = (
                    "deep-sort-realtime is unavailable; using deterministic dry-run tracker"
                )
                self.dry_run = True

    def update(
        self,
        frame: Any,
        detections: list[dict[str, Any]],
        frame_index: int,
        timestamp_ms: int | None = None,
    ) -> dict[str, Any]:
        filtered = self._filter_detections(detections)
        if not self.dry_run and self._real_tracker is not None:
            tracks = self._update_real_tracker(frame, filtered)
        else:
            tracks = self._update_dry_run(filtered)
        return {
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "tracks": tracks,
        }

    def reset(self) -> None:
        self._tracks.clear()
        self._next_track_id = 1
        if self._real_tracker is not None:
            self._real_tracker = self._load_real_tracker()

    def is_available(self) -> bool:
        return self.dry_run or self._real_tracker is not None

    def get_tracker_info(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "available": self.is_available(),
            "max_age": self.max_age,
            "n_init": self.n_init,
            "max_iou_distance": self.max_iou_distance,
            "max_cosine_distance": self.max_cosine_distance,
            "target_classes": sorted(self.target_classes) if self.target_classes else [],
            "min_confidence": self.min_confidence,
            "fallback_reason": self._fallback_reason,
        }

    def _filter_detections(
        self,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for detection in detections:
            class_name = str(detection.get("class_name", ""))
            confidence = float(detection.get("confidence", 0.0))
            bbox = detection.get("bbox", [])
            if self.target_classes and class_name not in self.target_classes:
                continue
            if confidence < self.min_confidence:
                continue
            if len(bbox) != 4:
                continue
            normalized = {
                "class_name": class_name,
                "class_id": detection.get("class_id"),
                "confidence": confidence,
                "bbox": [float(value) for value in bbox],
            }
            self._class_ids_by_name[class_name] = normalized["class_id"]
            filtered.append(normalized)
        return filtered

    def _update_dry_run(
        self,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        matched_track_ids: set[int] = set()
        active_outputs: list[dict[str, Any]] = []

        for detection in detections:
            track_id = self._match_detection_to_track(detection, matched_track_ids)
            if track_id is None:
                track = _TrackState(
                    track_id=self._next_track_id,
                    class_name=str(detection["class_name"]),
                    class_id=detection.get("class_id"),
                    confidence=float(detection["confidence"]),
                    bbox=list(detection["bbox"]),
                )
                self._tracks[track.track_id] = track
                self._next_track_id += 1
            else:
                track = self._tracks[track_id]
                track.class_name = str(detection["class_name"])
                track.class_id = detection.get("class_id")
                track.confidence = float(detection["confidence"])
                track.bbox = list(detection["bbox"])
                track.hits += 1
                track.missed = 0
            matched_track_ids.add(track.track_id)
            active_outputs.append(self._format_track(track, "confirmed"))

        lost_outputs: list[dict[str, Any]] = []
        for track_id in sorted(list(self._tracks)):
            if track_id in matched_track_ids:
                continue
            track = self._tracks[track_id]
            track.missed += 1
            if track.missed <= self.max_age:
                lost_outputs.append(self._format_track(track, "lost"))
            else:
                del self._tracks[track_id]

        return active_outputs + lost_outputs

    def _match_detection_to_track(
        self,
        detection: dict[str, Any],
        already_matched: set[int],
    ) -> int | None:
        best_track_id: int | None = None
        best_score = 0.0
        minimum_iou = max(0.0, 1.0 - self.max_iou_distance)
        for track_id in sorted(self._tracks):
            if track_id in already_matched:
                continue
            track = self._tracks[track_id]
            if track.class_name != detection["class_name"]:
                continue
            iou = _bbox_iou(track.bbox, detection["bbox"])
            center_score = _center_match_score(track.bbox, detection["bbox"])
            score = max(iou, center_score)
            if score > best_score:
                best_score = score
                best_track_id = track_id
        if best_track_id is None:
            return None
        return best_track_id if best_score >= minimum_iou else None

    def _update_real_tracker(
        self,
        frame: Any,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        deepsort_detections = []
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            deepsort_detections.append(
                ([x1, y1, x2 - x1, y2 - y1], detection["confidence"], detection["class_name"])
            )
        raw_tracks = self._real_tracker.update_tracks(deepsort_detections, frame=frame)
        tracks = []
        for raw_track in raw_tracks:
            if hasattr(raw_track, "is_confirmed") and not raw_track.is_confirmed():
                continue
            bbox = [float(value) for value in raw_track.to_ltrb()]
            class_name = str(getattr(raw_track, "det_class", "object") or "object")
            confidence = float(getattr(raw_track, "det_conf", 0.0) or 0.0)
            tracks.append(
                {
                    "track_id": int(raw_track.track_id),
                    "class_name": class_name,
                    "class_id": self._class_ids_by_name.get(class_name),
                    "confidence": confidence,
                    "bbox": bbox,
                    "center": _bbox_center(bbox),
                    "state": "confirmed",
                }
            )
        return tracks

    def _load_real_tracker(self) -> Any | None:
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
        except ImportError:
            return None
        return DeepSort(
            max_age=self.max_age,
            n_init=self.n_init,
            max_iou_distance=self.max_iou_distance,
            max_cosine_distance=self.max_cosine_distance,
        )

    def _format_track(self, track: _TrackState, state: str) -> dict[str, Any]:
        return {
            "track_id": track.track_id,
            "class_name": track.class_name,
            "class_id": track.class_id,
            "confidence": track.confidence,
            "bbox": [float(value) for value in track.bbox],
            "center": _bbox_center(track.bbox),
            "state": state if track.hits >= self.n_init else "tentative",
        }


def _bbox_center(bbox: list[float]) -> list[float]:
    x1, y1, x2, y2 = bbox
    return [(x1 + x2) / 2.0, (y1 + y2) / 2.0]


def _bbox_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_width = max(0.0, inter_x2 - inter_x1)
    inter_height = max(0.0, inter_y2 - inter_y1)
    intersection = inter_width * inter_height
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def _center_match_score(a: list[float], b: list[float]) -> float:
    ax, ay = _bbox_center(a)
    bx, by = _bbox_center(b)
    aw = max(1.0, a[2] - a[0])
    ah = max(1.0, a[3] - a[1])
    bw = max(1.0, b[2] - b[0])
    bh = max(1.0, b[3] - b[1])
    distance = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
    scale = max(aw, ah, bw, bh)
    return max(0.0, 1.0 - distance / scale)
