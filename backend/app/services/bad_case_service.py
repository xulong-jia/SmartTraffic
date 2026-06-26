from pathlib import Path
from datetime import UTC, datetime
import json
import os
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
from app.repositories import (
    BadCaseRepository,
    EvaluationResultRepository,
    EventRepository,
    ReviewCommentRepository,
    TrafficAnalysisRunRepository,
)


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
        session: Session | None = None,
    ) -> None:
        self.artifact_writer = artifact_writer
        self.eval_root = Path(eval_root or os.environ.get("SMARTTRAFFIC_EVALS_DIR", PROJECT_DIR / "evals"))
        self.session = session

    def status(self) -> dict[str, str]:
        return {"status": "ready", "stage": "stage_8b_bad_case_artifacts"}

    def create_bad_case(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        if self._db_run_exists(run_id):
            return self._create_db_bad_case(run_id=run_id, record=record)
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
        video_id: str | None = None,
        event_id: str | None = None,
        case_type: str | None = None,
        module: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        db_records = self._list_db_bad_cases(
            run_id=run_id,
            video_id=video_id,
            event_id=event_id,
            case_type=case_type,
            module=module,
            status=status,
            tag=tag,
            source=source,
        )
        if db_records:
            return db_records
        if run_id is not None and self._db_run_exists(run_id):
            return []
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
        if self._db_run_exists(run_id):
            return self._get_db_bad_case(case_id, run_id=run_id)
        return get_bad_case(self._existing_run_dir(run_id), case_id)

    def find_bad_case(self, *, case_id: str) -> dict[str, Any]:
        db_record = self._find_db_bad_case(case_id)
        if db_record is not None:
            return db_record
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
        if self._db_run_exists(run_id):
            return self._update_db_bad_case(
                run_id=run_id,
                case_id=case_id,
                updates=updates,
            )
        return update_bad_case(self._existing_run_dir(run_id), case_id, updates)

    def summarize_bad_cases(self, *, run_id: str | None = None) -> dict[str, Any]:
        return summarize_bad_case_records(self.list_bad_cases(run_id=run_id))

    def run_exists(self, run_id: str) -> bool:
        if self._db_run_exists(run_id):
            return True
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
        if self._db_run_exists(run_id):
            review = self._find_db_review(
                run_id=run_id,
                review_id=review_id,
                event_id=event_id,
            )
            inferred_case_type = case_type or _case_type_from_review(review)
            linked_event_id = str(review["event_id"]) if review.get("event_id") else None
            record = self._create_db_bad_case(
                run_id=run_id,
                record={
                    "event_id": linked_event_id,
                    "case_type": inferred_case_type,
                    "module": module,
                    "description": (
                        description
                        if description is not None
                        else _description_from_review(review)
                    ),
                    "expected_result": (
                        expected_result
                        if expected_result is not None
                        else _expected_result_from_review(review, inferred_case_type)
                    ),
                    "actual_result": (
                        actual_result
                        if actual_result is not None
                        else _actual_result_from_review(review)
                    ),
                    "tags": tags or ["review_center"],
                    "source": "review_center",
                    "linked_review_id": review["review_id"],
                },
            )
            return record
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
        if self._db_run_exists(run_id):
            existing = self._find_db_bad_case_by_failed_case(
                run_id=run_id,
                failed_case_id=failed_case_id,
            )
            if existing is not None:
                return existing
            failed_case = self._find_db_failed_case(
                run_id=run_id,
                failed_case_id=failed_case_id,
            )
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
            return self._create_db_bad_case(
                run_id=run_id,
                record={
                    "frame_index": frame_index,
                    "case_type": inferred_case_type,
                    "module": inferred_module,
                    "description": (
                        description
                        if description is not None
                        else _description_from_failed_case(failed_case)
                    ),
                    "expected_result": (
                        expected_result
                        if expected_result is not None
                        else _stringify_failed_case_side(failed_case.get("expected"))
                    ),
                    "actual_result": (
                        actual_result
                        if actual_result is not None
                        else _stringify_failed_case_side(failed_case.get("actual"))
                    ),
                    "root_cause": root_cause or "",
                    "tags": tags or ["evaluation"],
                    "source": "evaluation_center",
                    "linked_failed_case_id": failed_case_id,
                },
            )
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

    def _db_run_exists(self, run_id: str) -> bool:
        if self.session is None:
            return False
        try:
            return TrafficAnalysisRunRepository(self.session).get(run_id) is not None
        except SQLAlchemyError:
            return False

    def _create_db_bad_case(
        self,
        *,
        run_id: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        run = TrafficAnalysisRunRepository(self.session).get(run_id)  # type: ignore[arg-type]
        if run is None:
            raise KeyError(run_id)
        payload = dict(record)
        event_id = _string_or_none(payload.get("event_id"))
        event = EventRepository(self.session).get(event_id) if event_id else None  # type: ignore[arg-type]
        now = _utc_now_iso()
        case_id = str(payload.get("case_id") or f"badcase_{uuid4().hex[:12]}")
        payload.setdefault("case_id", case_id)
        payload.setdefault("run_id", run_id)
        payload.setdefault("video_id", payload.get("video_id") or run.video_id)
        payload.setdefault("event_id", event_id)
        payload.setdefault("track_id", _optional_int(getattr(event, "track_id", None)))
        payload.setdefault("frame_index", getattr(event, "frame_index", None))
        payload.setdefault("description", "")
        payload.setdefault("expected_result", "")
        payload.setdefault("actual_result", "")
        payload.setdefault("root_cause", "")
        payload.setdefault("snapshot_path", None)
        payload.setdefault("tags", [])
        payload.setdefault("status", "open")
        payload.setdefault("source", "manual")
        payload.setdefault("linked_review_id", None)
        payload.setdefault("linked_failed_case_id", None)
        payload.setdefault("created_at", now)
        payload.setdefault("updated_at", now)
        row = BadCaseRepository(self.session).create(  # type: ignore[arg-type]
            id=case_id,
            run_id=run_id,
            event_id=event_id,
            type=str(payload.get("case_type") or payload.get("type") or "other"),
            status=str(payload.get("status") or "open"),
            severity=_string_or_none(payload.get("severity") or getattr(event, "severity", None)),
            description=_string_or_none(payload.get("description")),
            tags=list(payload.get("tags") or []),
            payload=payload,
        )
        return _bad_case_from_model(row)

    def _list_db_bad_cases(
        self,
        *,
        run_id: str | None,
        video_id: str | None,
        event_id: str | None,
        case_type: str | None,
        module: str | None,
        status: str | None,
        tag: str | None,
        source: str | None,
    ) -> list[dict[str, Any]]:
        if self.session is None:
            return []
        try:
            rows = BadCaseRepository(self.session).list(
                run_id=run_id,
                event_id=event_id,
                type=case_type,
                status=status,
            )
        except SQLAlchemyError:
            return []
        records = [_bad_case_from_model(row) for row in rows]
        return [
            record
            for record in records
            if (video_id is None or record.get("video_id") == video_id)
            and (module is None or record.get("module") == module)
            and (source is None or record.get("source") == source)
            and (tag is None or tag in record.get("tags", []))
        ]

    def _get_db_bad_case(self, case_id: str, *, run_id: str | None = None) -> dict[str, Any]:
        record = self._find_db_bad_case(case_id)
        if record is None or (run_id is not None and record["run_id"] != run_id):
            raise KeyError(case_id)
        return record

    def _find_db_bad_case(self, case_id: str) -> dict[str, Any] | None:
        if self.session is None:
            return None
        try:
            row = BadCaseRepository(self.session).get(case_id)
        except SQLAlchemyError:
            return None
        return _bad_case_from_model(row) if row is not None else None

    def _update_db_bad_case(
        self,
        *,
        run_id: str,
        case_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        record = self._get_db_bad_case(case_id, run_id=run_id)
        sanitized = {
            key: value
            for key, value in dict(updates).items()
            if value is not None
            and key
            in {
                "status",
                "root_cause",
                "tags",
                "description",
                "expected_result",
                "actual_result",
                "snapshot_path",
                "linked_failed_case_id",
            }
        }
        if not sanitized:
            raise ValueError("no supported bad case fields to update")
        payload = {**record, **sanitized, "updated_at": _utc_now_iso()}
        row = BadCaseRepository(self.session).update(  # type: ignore[arg-type]
            case_id,
            status=payload["status"],
            description=payload.get("description"),
            tags=payload.get("tags") or [],
            payload=payload,
        )
        if row is None:
            raise KeyError(case_id)
        return _bad_case_from_model(row)

    def _find_db_review(
        self,
        *,
        run_id: str,
        review_id: str | None,
        event_id: str | None,
    ) -> dict[str, Any]:
        if self.session is None:
            raise KeyError(review_id or event_id or "")
        repo = ReviewCommentRepository(self.session)
        if review_id is not None:
            row = repo.get(review_id)
            if row is None or row.run_id != run_id:
                raise KeyError(review_id)
            return _review_from_model(row)
        if event_id is not None:
            rows = repo.list(run_id=run_id, event_id=event_id)
            if not rows:
                raise KeyError(event_id)
            return _review_from_model(rows[-1])
        raise ValueError("review_id or event_id is required")

    def _find_db_failed_case(
        self,
        *,
        run_id: str,
        failed_case_id: str,
    ) -> dict[str, Any]:
        if self.session is None:
            raise FailedCaseNotFound(failed_case_id)
        for row in EvaluationResultRepository(self.session).list(run_id=run_id):
            for failed_case in _failed_cases_from_result(row):
                if failed_case.get("failed_case_id") == failed_case_id:
                    return failed_case
        raise FailedCaseNotFound(failed_case_id)

    def _find_db_bad_case_by_failed_case(
        self,
        *,
        run_id: str,
        failed_case_id: str,
    ) -> dict[str, Any] | None:
        for record in self._list_db_bad_cases(
            run_id=run_id,
            video_id=None,
            event_id=None,
            case_type=None,
            module=None,
            status=None,
            tag=None,
            source=None,
        ):
            if record.get("linked_failed_case_id") == failed_case_id:
                return record
        return None

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


def _bad_case_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.setdefault("case_id", row.id)
    payload.setdefault("run_id", row.run_id)
    payload.setdefault("event_id", row.event_id)
    payload.setdefault("case_type", row.type)
    payload.setdefault("status", row.status)
    payload.setdefault("description", row.description or "")
    payload.setdefault("tags", row.tags or [])
    payload.setdefault("video_id", None)
    payload.setdefault("track_id", None)
    payload.setdefault("frame_index", None)
    payload.setdefault("module", "other")
    payload.setdefault("expected_result", "")
    payload.setdefault("actual_result", "")
    payload.setdefault("root_cause", "")
    payload.setdefault("snapshot_path", None)
    payload.setdefault("source", "manual")
    payload.setdefault("linked_review_id", None)
    payload.setdefault("linked_failed_case_id", None)
    payload.setdefault("created_at", _datetime_iso(row.created_at))
    payload.setdefault("updated_at", _datetime_iso(row.updated_at))
    return payload


def _review_from_model(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.setdefault("review_id", row.id)
    payload.setdefault("run_id", row.run_id)
    payload.setdefault("event_id", row.event_id)
    payload.setdefault("action", "comment")
    payload.setdefault("before_status", None)
    payload.setdefault("after_status", row.status)
    payload.setdefault("comment", row.body)
    payload.setdefault("reviewer", row.author or "local_reviewer")
    payload.setdefault("created_at", _datetime_iso(row.created_at))
    payload.setdefault("source", "review_center")
    return payload


def _failed_cases_from_result(row: Any) -> list[dict[str, Any]]:
    summary = row.summary or {}
    failed_cases = summary.get("failed_cases")
    if isinstance(failed_cases, list):
        return [item for item in failed_cases if isinstance(item, dict)]
    metrics = row.metrics or {}
    details = metrics.get("details")
    if isinstance(details, dict) and isinstance(details.get("failed_cases"), list):
        return [item for item in details["failed_cases"] if isinstance(item, dict)]
    return []


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _datetime_iso(value: datetime | None) -> str:
    if value is None:
        return _utc_now_iso()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).replace(microsecond=0).isoformat()
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
