from pathlib import Path
from typing import Any

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.review_artifacts import (
    append_false_negative,
    apply_review_action,
    load_event_review_state,
    load_false_negatives,
    load_review_comments,
)
from app.core.config import get_settings


class ReviewService:
    """Stage 7B artifact-backed review state helper.

    This service intentionally does not expose Review API behavior yet. Stage 7C
    will translate these artifact operations into HTTP contracts.
    """

    def __init__(self, artifact_writer: TrafficArtifactWriter | None = None) -> None:
        self.artifact_writer = artifact_writer

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_7b_review_artifacts"}

    def list_review_comments(self, *, run_id: str) -> list[dict[str, Any]]:
        return load_review_comments(self._run_dir(run_id))

    def event_review_state(self, *, run_id: str) -> dict[str, Any]:
        return load_event_review_state(self._run_dir(run_id), run_id=run_id)

    def apply_action(
        self,
        *,
        run_id: str,
        event_id: str,
        action: str,
        comment: str | None = None,
        reviewer: str | None = None,
        alert_id: str | None = None,
        source: str = "review_center",
    ) -> dict[str, Any]:
        return apply_review_action(
            self._run_dir(run_id),
            run_id=run_id,
            event_id=event_id,
            action=action,
            comment=comment,
            reviewer=reviewer,
            alert_id=alert_id,
            source=source,
        )

    def add_false_negative(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return append_false_negative(
            self._run_dir(run_id),
            {
                **record,
                "run_id": run_id,
            },
        )

    def list_false_negatives(self, *, run_id: str) -> list[dict[str, Any]]:
        return load_false_negatives(self._run_dir(run_id))

    def _run_dir(self, run_id: str) -> Path:
        return self._writer().base_dir / run_id

    def _writer(self) -> TrafficArtifactWriter:
        return self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)
