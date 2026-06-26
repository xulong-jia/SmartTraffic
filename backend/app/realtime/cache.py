from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Any


class RealtimePreviewCache:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self._frames: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_items)
        )
        self._events: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_items)
        )
        self._alerts: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_items)
        )

    def replace(
        self,
        camera_id: str,
        *,
        frames: Iterable[dict[str, Any]],
        events: Iterable[dict[str, Any]],
        alerts: Iterable[dict[str, Any]],
    ) -> None:
        self.clear(camera_id)
        for frame in frames:
            self._frames[camera_id].append(dict(frame))
        for event in events:
            self._events[camera_id].append(dict(event))
        for alert in alerts:
            self._alerts[camera_id].append(dict(alert))

    def recent_frames(self, camera_id: str) -> list[dict[str, Any]]:
        return list(self._frames[camera_id])

    def recent_events(self, camera_id: str) -> list[dict[str, Any]]:
        return list(self._events[camera_id])

    def recent_alerts(self, camera_id: str) -> list[dict[str, Any]]:
        return list(self._alerts[camera_id])

    def clear(self, camera_id: str) -> None:
        self._frames.pop(camera_id, None)
        self._events.pop(camera_id, None)
        self._alerts.pop(camera_id, None)


realtime_preview_cache = RealtimePreviewCache(max_items=20)
