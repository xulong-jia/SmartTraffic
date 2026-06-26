from collections.abc import Generator
import json
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from app.repositories import (
    BadCaseRepository,
    EvaluationDatasetRepository,
    EvaluationResultRepository,
    TrafficAnalysisRunRepository,
    VideoRepository,
)


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage3ef-evaluation.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("SMARTTRAFFIC_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("SMARTTRAFFIC_EVALS_DIR", str(tmp_path / "evals"))

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


def test_evaluation_db_run_results_summary_failed_cases_and_not_applicable(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    with session_factory() as session:
        _seed_run(session, tmp_path)
        session.commit()
    _write_expected_events(tmp_path)

    registered = client.post(
        "/api/evaluation/datasets",
        json={
            "dataset_id": "dataset-db",
            "name": "DB Dataset",
            "dataset_type": "event",
            "expected_events_path": "expected/events.json",
        },
    )
    run_response = client.post(
        "/api/evaluation/run",
        json={
            "run_id": "run-eval-db",
            "dataset_id": "dataset-db",
            "evaluation_type": "event",
        },
    )
    detection_response = client.post(
        "/api/evaluation/run",
        json={"run_id": "run-eval-db", "evaluation_type": "detection"},
    )
    results = client.get("/api/evaluation/results?run_id=run-eval-db")
    summary = client.get("/api/evaluation/summary/run-eval-db")
    failed_cases = client.get("/api/evaluation/failed-cases?run_id=run-eval-db")

    assert registered.status_code == 200
    assert run_response.status_code == 200
    assert run_response.json()["evaluation_run"]["status"] == "completed"
    assert detection_response.status_code == 200
    detection_result = detection_response.json()["results"][0]
    assert detection_result["metric_name"] == "detection_status"
    assert detection_result["details"]["status"] == "not_applicable"
    assert results.status_code == 200
    assert {item["metric_name"] for item in results.json()["items"]} >= {
        "event_precision",
        "event_recall",
        "detection_status",
    }
    assert summary.status_code == 200
    assert summary.json()["summary"]["event"]["event_precision"]["run_id"] == "run-eval-db"
    assert failed_cases.status_code == 200
    assert any(
        item["failure_type"] == "false_negative"
        for item in failed_cases.json()["items"]
    )

    with session_factory() as session:
        assert EvaluationDatasetRepository(session).get("dataset-db") is not None
        stored_results = EvaluationResultRepository(session).list(run_id="run-eval-db")
        assert len(stored_results) >= 4
        assert any(
            result.summary and result.summary.get("failed_cases")
            for result in stored_results
        )


def test_failed_case_to_bad_case_db_is_idempotent(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    with session_factory() as session:
        _seed_run(session, tmp_path)
        EvaluationDatasetRepository(session).create(
            id="dataset-failed",
            name="Failed Dataset",
            dataset_type="event",
            status="active",
            config={},
        )
        EvaluationResultRepository(session).create(
            id="eval-result-failed",
            dataset_id="dataset-failed",
            run_id="run-eval-db",
            evaluation_type="event",
            status="completed",
            metrics={"event_recall": 0.0},
            summary={
                "evaluation_run_id": "eval-run-failed",
                "failed_cases": [
                    {
                        "failed_case_id": "failed-db-1",
                        "evaluation_run_id": "eval-run-failed",
                        "run_id": "run-eval-db",
                        "dataset_id": "dataset-failed",
                        "failure_type": "false_negative",
                        "module": "event_engine",
                        "expected": {"event_type": "illegal_parking"},
                        "actual": {},
                        "frame_range": {"start_frame": 5, "end_frame": 8},
                        "suggested_bad_case_type": "false_negative",
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
            },
        )
        session.commit()

    first = client.post(
        "/api/bad-cases/from-failed-case",
        json={
            "run_id": "run-eval-db",
            "failed_case_id": "failed-db-1",
            "module": "evaluation",
            "tags": ["evaluation"],
        },
    )
    second = client.post(
        "/api/bad-cases/from-failed-case",
        json={"run_id": "run-eval-db", "failed_case_id": "failed-db-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["case_id"] == first.json()["case_id"]
    assert first.json()["linked_failed_case_id"] == "failed-db-1"

    with session_factory() as session:
        cases = BadCaseRepository(session).list(run_id="run-eval-db")
        assert len(cases) == 1


def test_run_evals_cli_can_write_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cli-evals.db"
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as session:
        _seed_run(session, tmp_path)
        session.commit()

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--run-id",
            "run-eval-db",
            "--evaluation-type",
            "trajectory",
            "--results-root",
            str(tmp_path / "results"),
            "--eval-root",
            str(tmp_path / "evals"),
            "--database-url",
            database_url,
            "--write-db",
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["evaluation_run"]["run_id"] == "run-eval-db"

    with factory() as session:
        rows = EvaluationResultRepository(session).list(run_id="run-eval-db")
        assert rows
        assert rows[0].evaluation_type == "trajectory"


def _seed_run(session: Session, tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "run-eval-db"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": "run-eval-db", "video_id": "video-eval-db"}),
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "actual-event",
                "run_id": "run-eval-db",
                "video_id": "video-eval-db",
                "event_type": "wrong_way_driving",
                "start_frame": 10,
                "end_frame": 12,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "trajectory_points.jsonl").write_text(
        json.dumps(
            {
                "frame_index": 1,
                "track_id": 1,
                "track_length": 2,
                "speed_px_per_second": 12,
                "moving_angle": 90,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    VideoRepository(session).create(
        id="video-eval-db",
        filename="eval.mp4",
        storage_path="local_videos/eval.mp4",
        status="completed",
    )
    TrafficAnalysisRunRepository(session).create(
        id="run-eval-db",
        video_id="video-eval-db",
        status="completed",
        result_dir=str(run_dir),
        artifact_index={},
    )


def _write_expected_events(tmp_path: Path) -> None:
    path = tmp_path / "evals" / "expected" / "events.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_id": "expected-event",
                        "event_type": "illegal_parking",
                        "start_frame": 40,
                        "end_frame": 50,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
