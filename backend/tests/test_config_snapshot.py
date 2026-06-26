from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.repositories import TrafficAnalysisRunRepository, VideoRepository
from app.services.config_snapshot_service import (
    attach_config_snapshot_to_run,
    build_config_snapshot,
)
from app.services.event_rule_service import EventRuleDbService
from app.services.zone_service import ZoneDbService


def test_build_and_attach_config_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        VideoRepository(session).create(
            id="video-snapshot-1",
            filename="snapshot.mp4",
            storage_path="local_videos/snapshot.mp4",
            status="uploaded",
        )
        ZoneDbService(session).create_zone(
            {
                "id": "zone-snapshot-1",
                "name": "Snapshot lane",
                "zone_type": "vehicle_lane",
                "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
                "video_id": "video-snapshot-1",
                "version": 7,
            }
        )
        EventRuleDbService(session).create_rule(
            {
                "id": "rule-snapshot-1",
                "name": "Snapshot flow",
                "event_type": "flow_counting",
                "zone_id": "zone-snapshot-1",
                "version": 8,
            }
        )
        run = TrafficAnalysisRunRepository(session).create(
            id="run-snapshot-1",
            video_id="video-snapshot-1",
            status="created",
            result_dir="results/traffic_analysis/run-snapshot-1",
            artifact_index={},
            summary={"existing": "kept"},
        )

        snapshot = build_config_snapshot(session, video_id="video-snapshot-1")
        assert snapshot["zones"][0]["id"] == "zone-snapshot-1"
        assert snapshot["zones"][0]["version"] == 7
        assert snapshot["event_rules"][0]["id"] == "rule-snapshot-1"
        assert snapshot["event_rules"][0]["version"] == 8

        attach_config_snapshot_to_run(session, run.id, snapshot)
        stored = TrafficAnalysisRunRepository(session).get(run.id)
        assert stored.summary["existing"] == "kept"
        assert stored.summary["event_config_snapshot"] == snapshot
