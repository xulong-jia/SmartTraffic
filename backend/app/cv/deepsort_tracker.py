from typing import Any


class DeepSortTracker:
    """Interface placeholder. Full DeepSORT runtime is out of scope for phase one."""

    def update(self, detections: list[dict[str, Any]], frame: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("DeepSORT tracking is planned for a later phase")
