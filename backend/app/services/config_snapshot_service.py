from typing import Any

from sqlalchemy.orm import Session

from app.repositories import TrafficAnalysisRunRepository
from app.services.event_rule_service import EventRuleDbService
from app.services.zone_service import ZoneDbService


def build_config_snapshot(
    session: Session,
    *,
    video_id: str | None = None,
    camera_id: str | None = None,
) -> dict[str, Any]:
    zone_service = ZoneDbService(session)
    event_rule_service = EventRuleDbService(session)
    zones = zone_service.list_zones(
        video_id=video_id,
        camera_id=camera_id,
        enabled=True,
    )
    event_rules = event_rule_service.list_rules(enabled=True)
    if video_id is not None:
        zone_ids = {zone["id"] for zone in zones}
        event_rules = [
            rule
            for rule in event_rules
            if rule.get("zone_id") is None or rule.get("zone_id") in zone_ids
        ]
    return {
        "schema_version": "stage3.config_snapshot.v1",
        "video_id": video_id,
        "camera_id": camera_id,
        "zones": zones,
        "event_rules": event_rules,
    }


def attach_config_snapshot_to_run(
    session: Session,
    run_id: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    repo = TrafficAnalysisRunRepository(session)
    run = repo.get(run_id)
    if run is None:
        raise KeyError(run_id)
    summary = dict(run.summary or {})
    summary["event_config_snapshot"] = snapshot
    repo.update(run_id, summary=summary)
    return summary
