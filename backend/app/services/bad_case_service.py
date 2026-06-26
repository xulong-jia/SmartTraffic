from pathlib import Path
import json
import os
from typing import Any

from app.analysis.artifact_writer import TrafficArtifactWriter
from app.analysis.bad_case_artifacts import (
    append_bad_case,
    filter_bad_cases,
    get_bad_case,
    load_bad_cases,
    summarize_bad_case_records,
    update_bad_case,
)
from app.analysis.evaluation_artifacts import load_failed_cases
from app.analysis.review_artifacts import load_review_comments
from app.core.config import get_settings
from app.core.paths import PROJECT_DIR


class FailedCaseNotFound(KeyError):
    """Raised when an Evaluation failed case cannot be found."""


class BadCaseService:
    """Stage 8B artifact-backed Bad Case helper.

    The service writes local run artifacts only. API endpoints, frontend flows,
    Evaluation Center metrics, and database persistence remain later stages.
    """

    def __init__(
        self,
        artifact_writer: TrafficArtifactWriter | None = None,
        *,
        eval_root: str | Path | None = None,
    ) -> None:
        self.artifact_writer = artifact_writer
        self.eval_root = Path(eval_root or os.environ.get("SMARTTRAFFIC_EVALS_DIR", PROJECT_DIR / "evals"))

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_8b_bad_case_artifacts"}

    def create_bad_case(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        return append_bad_case(
            run_dir,
            {
                **record,
                "run_id": run_id,
                "video_id": record.get("video_id") or self._video_id(run_dir),
            },
        )

    def list_bad_cases(
        self,
        *,
        run_id: str | None = None,
        case_type: str | None = None,
        module: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        if run_id is not None:
            records = load_bad_cases(self._existing_run_dir(run_id))
        else:
            records = []
            for run_dir in self._iter_run_dirs():
                records.extend(load_bad_cases(run_dir))
        return filter_bad_cases(
            records,
            case_type=case_type,
            module=module,
            status=status,
            tag=tag,
            source=source,
        )

    def get_bad_case(self, *, run_id: str, case_id: str) -> dict[str, Any]:
        return get_bad_case(self._existing_run_dir(run_id), case_id)

    def find_bad_case(self, *, case_id: str) -> dict[str, Any]:
        for record in self.list_bad_cases():
            if record["case_id"] == case_id:
                return record
        raise KeyError(case_id)

    def update_bad_case(
        self,
        *,
        run_id: str,
        case_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return update_bad_case(self._existing_run_dir(run_id), case_id, updates)

    def summarize_bad_cases(self, *, run_id: str | None = None) -> dict[str, Any]:
        return summarize_bad_case_records(self.list_bad_cases(run_id=run_id))

    def run_exists(self, run_id: str) -> bool:
        return self._run_dir(run_id).is_dir()

    def create_bad_case_from_review(
        self,
        *,
        run_id: str,
        review_id: str | None = None,
        event_id: str | None = None,
        case_type: str | None = None,
        module: str = "review_center",
        description: str | None = None,
        expected_result: str | None = None,
        actual_result: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        review = self._find_review(run_dir, review_id=review_id, event_id=event_id)
        inferred_case_type = case_type or _case_type_from_review(review)
        linked_event_id = str(review["event_id"]) if review.get("event_id") else None
        return append_bad_case(
            run_dir,
            {
                "run_id": run_id,
                "video_id": self._video_id(run_dir),
                "event_id": linked_event_id,
                "case_type": inferred_case_type,
                "module": module,
                "description": description
                if description is not None
                else _description_from_review(review),
                "expected_result": expected_result
                if expected_result is not None
                else _expected_result_from_review(review, inferred_case_type),
                "actual_result": actual_result
                if actual_result is not None
                else _actual_result_from_review(review),
                "tags": tags or ["review_center"],
                "source": "review_center",
                "linked_review_id": review["review_id"],
            },
        )

    def create_bad_case_from_failed_case(
        self,
        *,
        run_id: str,
        failed_case_id: str,
        case_type: str | None = None,
        module: str | None = None,
        description: str | None = None,
        expected_result: str | None = None,
        actual_result: str | None = None,
        root_cause: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._existing_run_dir(run_id)
        existing = self._find_bad_case_by_failed_case(
            run_id=run_id,
            failed_case_id=failed_case_id,
        )
        if existing is not None:
            return existing

        failed_case = self._find_failed_case(run_id=run_id, failed_case_id=failed_case_id)
        inferred_case_type = case_type or str(
            failed_case.get("suggested_bad_case_type")
            or failed_case.get("failure_type")
            or "other"
        )
        inferred_module = module or str(failed_case.get("module") or "other")
        frame_range = failed_case.get("frame_range")
        frame_index = None
        if isinstance(frame_range, dict):
            frame_index = frame_range.get("start_frame") or frame_range.get("end_frame")

        return append_bad_case(
            run_dir,
            {
                "run_id": run_id,
                "video_id": self._video_id(run_dir),
                "frame_index": frame_index,
                "case_type": inferred_case_type,
                "module": inferred_module,
                "description": description
                if description is not None
                else _description_from_failed_case(failed_case),
                "expected_result": expected_result
                if expected_result is not None
                else _stringify_failed_case_side(failed_case.get("expected")),
                "actual_result": actual_result
                if actual_result is not None
                else _stringify_failed_case_side(failed_case.get("actual")),
                "root_cause": root_cause or "",
                "tags": tags or ["evaluation"],
                "source": "evaluation_center",
                "linked_failed_case_id": failed_case_id,
            },
        )

    def _find_bad_case_by_failed_case(
        self,
        *,
        run_id: str,
        failed_case_id: str,
    ) -> dict[str, Any] | None:
        for record in self.list_bad_cases(run_id=run_id):
            if record.get("linked_failed_case_id") == failed_case_id:
                return record
        return None

    def _find_failed_case(
        self,
        *,
        run_id: str,
        failed_case_id: str,
    ) -> dict[str, Any]:
        for failed_case in load_failed_cases(self.eval_root):
            if (
                failed_case.get("failed_case_id") == failed_case_id
                and failed_case.get("run_id") == run_id
            ):
                return failed_case
        raise FailedCaseNotFound(failed_case_id)

    def _find_review(
        self,
        run_dir: Path,
        *,
        review_id: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        comments = load_review_comments(run_dir)
        if review_id is not None:
            for comment in comments:
                if comment.get("review_id") == review_id:
                    return comment
            raise KeyError(review_id)
        if event_id is not None:
            for comment in reversed(comments):
                if comment.get("event_id") == event_id:
                    return comment
            raise KeyError(event_id)
        raise ValueError("review_id or event_id is required")

    def _run_dir(self, run_id: str) -> Path:
        return self._writer().base_dir / run_id

    def _existing_run_dir(self, run_id: str) -> Path:
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            raise KeyError(run_id)
        return run_dir

    def _iter_run_dirs(self) -> list[Path]:
        base_dir = self._writer().base_dir
        if not base_dir.is_dir():
            return []
        return sorted(path for path in base_dir.iterdir() if path.is_dir())

    def _video_id(self, run_dir: Path) -> str | None:
        metadata_path = run_dir / "metadata.json"
        if not metadata_path.is_file():
            return None
        with metadata_path.open(encoding="utf-8") as file:
            metadata = json.load(file)
        value = metadata.get("video_id") if isinstance(metadata, dict) else None
        return str(value) if value else None

    def _writer(self) -> TrafficArtifactWriter:
        return self.artifact_writer or TrafficArtifactWriter(get_settings().results_dir)


def _case_type_from_review(review: dict[str, Any]) -> str:
    after_status = str(review.get("after_status") or "")
    if after_status in {"false_positive", "false_negative"}:
        return after_status
    action = str(review.get("action") or "")
    if action == "add_false_negative":
        return "false_negative"
    return "false_positive"


def _description_from_review(review: dict[str, Any]) -> str:
    comment = str(review.get("comment") or "").strip()
    if comment:
        return comment
    event_id = review.get("event_id")
    return f"Bad Case created from review {review['review_id']} for event {event_id}."


def _expected_result_from_review(review: dict[str, Any], case_type: str) -> str:
    if case_type == "false_positive":
        return "event should not be accepted as a true positive"
    if case_type == "false_negative":
        return "expected event should be represented in Stage 6/7 artifacts"
    before_status = review.get("before_status")
    return f"reviewed result should differ from {before_status}"


def _actual_result_from_review(review: dict[str, Any]) -> str:
    after_status = review.get("after_status")
    if after_status:
        return f"review marked artifact as {after_status}"
    action = review.get("action")
    return f"review action recorded as {action}"


def _description_from_failed_case(failed_case: dict[str, Any]) -> str:
    failure_type = failed_case.get("failure_type")
    return f"Converted from evaluation failed case {failed_case['failed_case_id']} ({failure_type})."


def _stringify_failed_case_side(value: Any) -> str:
    if value in (None, {}, []):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
