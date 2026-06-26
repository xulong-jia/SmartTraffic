import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models as models


EXPECTED_TABLES = {
    "videos",
    "cameras",
    "frames",
    "processing_tasks",
    "traffic_analysis_runs",
    "model_runs",
    "detections",
    "tracks",
    "trajectory_points",
    "zones",
    "event_rules",
    "events",
    "event_evidence",
    "rule_executions",
    "alerts",
    "flow_counts",
    "zone_statistics",
    "review_comments",
    "bad_cases",
    "evaluation_datasets",
    "evaluation_results",
}


EXPECTED_MODEL_NAMES = {
    "Alert",
    "BadCase",
    "Camera",
    "Detection",
    "EvaluationDataset",
    "EvaluationResult",
    "Event",
    "EventEvidence",
    "EventRule",
    "FlowCount",
    "Frame",
    "ModelRun",
    "ProcessingTask",
    "ReviewComment",
    "RuleExecution",
    "Track",
    "TrafficAnalysisRun",
    "TrajectoryPoint",
    "Video",
    "Zone",
    "ZoneStatistic",
}


def test_model_exports_and_metadata_cover_core_tables():
    for name in EXPECTED_MODEL_NAMES:
        assert hasattr(models, name), name

    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))


def test_create_all_and_json_fields_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'models.db'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        zone = models.Zone(
            id="zone-1",
            name="Intersection A",
            type="polygon",
            coordinates={"points": [[0, 0], [10, 0], [10, 10], [0, 10]]},
            metadata_json={"camera": "cam-1"},
        )
        session.add(zone)
        session.commit()

        stored = session.execute(select(models.Zone).where(models.Zone.id == "zone-1")).scalar_one()
        assert stored.coordinates["points"][2] == [10, 10]
        assert stored.metadata_json["camera"] == "cam-1"


def test_alembic_upgrade_downgrade_upgrade_on_temp_sqlite(tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "alembic-1cd.db"
    env = {
        **os.environ,
        "SMARTTRAFFIC_DATABASE_URL": f"sqlite:///{database_path}",
    }

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "-1"],
        cwd=backend_dir,
        env=env,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
    )

    engine = create_engine(f"sqlite:///{database_path}", future=True)
    with engine.connect() as connection:
        table_names = set(connection.dialect.get_table_names(connection))

    assert EXPECTED_TABLES.issubset(table_names)
