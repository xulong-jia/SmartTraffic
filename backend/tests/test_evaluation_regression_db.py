import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.repositories import (
    BadCaseRepository,
    EvaluationResultRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)
from app.services.bad_case_service import BadCaseService
from app.services.evaluation_service import EvaluationService


def test_regression_evaluation_persists_metrics_and_failed_cases_without_status_updates(
    tmp_path: Path,
) -> None:
    with _session_factory(tmp_path)() as session:
        _seed_run(session, tmp_path)
        _seed_regression_cases(session)
        session.commit()

        service = EvaluationService(results_dir=tmp_path / "results", eval_root=tmp_path / "evals", session=session)
        response = service.run_evaluation(
            run_id="run-regression-db",
            evaluation_type="regression",
            config={"case_type": "false_positive", "apply_updates": False},
        )
        session.commit()

        regression = response["summary"]["summary"]["bad_case_regression"]
        metric_names = {result["metric_name"] for result in response["results"]}
        assert {
            "bad_case_regression_pass_rate",
            "bad_case_regression_total_cases",
            "bad_case_regression_failed_cases",
            "bad_case_regression_fixed_cases",
            "bad_case_regression_reopened_cases",
        } <= metric_names
        assert regression["total_case_count"] == 2
        assert regression["passed_case_count"] == 1
        assert regression["failed_case_count"] == 1
        assert regression["fixed_case_count"] == 1
        assert regression["reopened_case_count"] == 1
        assert response["failed_cases"][0]["failure_type"] == "regression_failed"

        rows = EvaluationResultRepository(session).list(run_id="run-regression-db", evaluation_type="regression")
        assert rows
        assert any(row.summary and row.summary.get("failed_cases") for row in rows)
        assert BadCaseService(session=session).get_bad_case(
            run_id="run-regression-db",
            case_id="case-open-pass",
        )["status"] == "open"
        assert BadCaseService(session=session).get_bad_case(
            run_id="run-regression-db",
            case_id="case-fixed-fail",
        )["status"] == "fixed"


def test_regression_evaluation_apply_updates_marks_fixed_and_reopens_existing_cases(
    tmp_path: Path,
) -> None:
    with _session_factory(tmp_path)() as session:
        _seed_run(session, tmp_path)
        _seed_regression_cases(session)
        session.commit()

        service = EvaluationService(results_dir=tmp_path / "results", eval_root=tmp_path / "evals", session=session)
        response = service.run_evaluation(
            run_id="run-regression-db",
            evaluation_type="regression",
            config={"apply_updates": True},
        )
        session.commit()

        regression = response["summary"]["summary"]["bad_case_regression"]
        assert regression["apply_updates"] is True
        assert regression["updated_case_count"] == 2
        assert BadCaseService(session=session).get_bad_case(
            run_id="run-regression-db",
            case_id="case-open-pass",
        )["status"] == "fixed"
        assert BadCaseService(session=session).get_bad_case(
            run_id="run-regression-db",
            case_id="case-fixed-fail",
        )["status"] == "open"


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'regression.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def _seed_run(session: Session, tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "run-regression-db"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": "run-regression-db", "video_id": "video-regression-db"}),
        encoding="utf-8",
    )
    VideoRepository(session).create(
        id="video-regression-db",
        filename="regression.mp4",
        storage_path="local_videos/regression.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-regression-db",
        video_id="video-regression-db",
        status="completed",
        result_dir=str(run_dir),
        artifact_index={},
    )


def _seed_regression_cases(session: Session) -> None:
    repo = BadCaseRepository(session)
    repo.create(
        id="case-open-pass",
        run_id="run-regression-db",
        event_id=None,
        type="false_positive",
        status="open",
        severity=None,
        description="Open false positive should be fixed by replay.",
        tags=["stage4e", "event"],
        payload={
            "case_id": "case-open-pass",
            "run_id": "run-regression-db",
            "case_type": "false_positive",
            "module": "event_engine",
            "status": "open",
            "expected_result": "no event",
            "actual_result": "event emitted",
            "tags": ["stage4e", "event"],
            "regression_replay": {"actual_result": "no event"},
        },
    )
    repo.create(
        id="case-fixed-fail",
        run_id="run-regression-db",
        event_id=None,
        type="false_positive",
        status="fixed",
        severity=None,
        description="Fixed false positive regressed.",
        tags=["stage4e", "event"],
        payload={
            "case_id": "case-fixed-fail",
            "run_id": "run-regression-db",
            "case_type": "false_positive",
            "module": "event_engine",
            "status": "fixed",
            "expected_result": "no event",
            "actual_result": "no event",
            "tags": ["stage4e", "event"],
            "regression_replay": {"actual_result": "event emitted"},
        },
    )
    repo.create(
        id="case-ignored",
        run_id="run-regression-db",
        event_id=None,
        type="id_switch",
        status="ignored",
        severity=None,
        description="Ignored tracker case.",
        tags=["stage4e", "tracker"],
        payload={
            "case_id": "case-ignored",
            "run_id": "run-regression-db",
            "case_type": "id_switch",
            "module": "tracker",
            "status": "ignored",
            "expected_result": "stable id",
            "actual_result": "id switch",
            "tags": ["stage4e", "tracker"],
            "regression_replay": {"actual_result": "stable id"},
        },
    )
