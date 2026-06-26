from app.events.engine import EventEngine
from app.events.rules import EventRule


def test_wrong_way_requires_confirm_frames_and_uses_trajectory_features() -> None:
    engine = EventEngine(run_id="run-final", video_id="video-final", record_not_matched=True)
    rule = EventRule(
        rule_id="wrong-final",
        name="Wrong way final",
        event_type="wrong_way_driving",
        severity="high",
        target_classes=("car", "bus", "truck", "motorcycle"),
        zone_id="lane-1",
        parameters={
            "allowed_angle": 0,
            "reverse_angle_threshold": 135,
            "confirm_frames": 2,
            "min_speed": 1.0,
        },
    )

    first = engine.update(
        _frame(1, [_point(moving_angle=180, speed=4.0)]),
        rules=[rule],
        zones=[_zone("lane-1", "vehicle_lane")],
    )
    second = engine.update(
        _frame(2, [_point(moving_angle=182, speed=4.0)]),
        rules=[rule],
        zones=[_zone("lane-1", "vehicle_lane")],
    )

    assert first["events"] == []
    assert first["rule_executions"][0]["output_result"]["reason"] == "confirm_frames_not_met"
    assert len(second["events"]) == 1
    evidence = second["event_evidence"][0]["evidence_json"]
    assert evidence["angle_diff"] >= 135
    assert evidence["allowed_angle"] == 0.0
    assert evidence["moving_angle"] == 182.0
    assert evidence["speed_px_per_frame"] == 4.0
    assert evidence["confirm_frames"] == 2
    assert evidence["zone_id"] == "lane-1"


def test_zone_rules_require_inside_duration_and_parking_center_shift() -> None:
    engine = EventEngine(run_id="run-final", video_id="video-final", record_not_matched=True)
    danger_rule = EventRule(
        rule_id="danger-final",
        name="Danger final",
        event_type="danger_zone_intrusion",
        target_classes=("person",),
        zone_id="danger-1",
        parameters={"min_inside_frames": 2, "min_inside_seconds": 0.2},
    )
    parking_rule = EventRule(
        rule_id="parking-final",
        name="Parking final",
        event_type="illegal_parking",
        target_classes=("car",),
        zone_id="parking-1",
        parameters={
            "min_dwell_seconds": 0.2,
            "stop_speed_threshold": 1.0,
            "max_center_shift": 2.0,
            "zone_types": ["no_parking_zone", "vehicle_lane"],
        },
    )

    first = engine.update(
        _frame(
            1,
            [
                _point(track_id=1, class_name="person", zone_id="danger-1", inside_frames=1),
                _point(
                    track_id=2,
                    class_name="car",
                    zone_id="parking-1",
                    speed=0.2,
                    dwell_time_ms=100,
                    center_shift=1.0,
                ),
            ],
        ),
        rules=[danger_rule, parking_rule],
        zones=[
            _zone("danger-1", "danger_zone"),
            _zone("parking-1", "no_parking_zone"),
        ],
    )
    second = engine.update(
        _frame(
            2,
            [
                _point(track_id=1, class_name="person", zone_id="danger-1", inside_frames=2),
                _point(
                    track_id=2,
                    class_name="car",
                    zone_id="parking-1",
                    speed=0.2,
                    dwell_time_ms=250,
                    center_shift=1.0,
                ),
            ],
        ),
        rules=[danger_rule, parking_rule],
        zones=[
            _zone("danger-1", "danger_zone"),
            _zone("parking-1", "no_parking_zone"),
        ],
    )

    assert first["events"] == []
    assert {
        item["output_result"]["reason"]
        for item in first["rule_executions"]
        if item["status"] != "skipped"
    } == {
        "inside_duration_not_enough",
        "dwell_time_not_enough",
    }
    assert {event["event_type"] for event in second["events"]} == {
        "danger_zone_intrusion",
        "illegal_parking",
    }
    parking_evidence = [
        item["evidence_json"]
        for item in second["event_evidence"]
        if item["event_type"] == "illegal_parking"
    ][0]
    assert parking_evidence["center_shift"] == 1.0
    assert parking_evidence["max_center_shift"] == 2.0


def test_pedestrian_congestion_and_flow_counting_final_behavior() -> None:
    engine = EventEngine(run_id="run-final", video_id="video-final", record_not_matched=True)
    pedestrian_rule = EventRule(
        rule_id="ped-final",
        name="Pedestrian final",
        event_type="pedestrian_in_vehicle_lane",
        zone_id="lane-1",
        parameters={"min_inside_frames": 2, "point_type": "bottom_center"},
    )
    congestion_rule = EventRule(
        rule_id="congestion-final",
        name="Congestion final",
        event_type="congestion",
        zone_id="lane-1",
        parameters={
            "rule_mode": "aggregate",
            "vehicle_count_threshold": 2,
            "avg_speed_threshold": 1.0,
            "time_window_seconds": 0.2,
        },
    )
    flow_rule = EventRule(
        rule_id="flow-final",
        name="Flow final",
        event_type="flow_counting",
        parameters={
            "line_id": "line-1",
            "direction": "positive",
            "same_track_cooldown_frames": 3,
        },
    )

    first = engine.update(
        _frame(
            1,
            [
                _point(track_id=10, class_name="person", zone_id="lane-1", inside_frames=1),
                _point(track_id=11, class_name="car", zone_id="lane-1", speed=0.5),
                _point(track_id=12, class_name="bus", zone_id="lane-1", speed=0.7),
                _point(
                    track_id=13,
                    class_name="car",
                    speed=0.5,
                    line_crossings=[
                        {
                            "line_id": "line-1",
                            "direction": "positive",
                            "frame_index": 1,
                        }
                    ],
                ),
            ],
        ),
        rules=[pedestrian_rule, congestion_rule, flow_rule],
        zones=[_zone("lane-1", "vehicle_lane")],
    )
    second = engine.update(
        _frame(
            2,
            [
                _point(track_id=10, class_name="person", zone_id="lane-1", inside_frames=2),
                _point(track_id=11, class_name="car", zone_id="lane-1", speed=0.5),
                _point(track_id=12, class_name="bus", zone_id="lane-1", speed=0.7),
                _point(
                    track_id=13,
                    class_name="car",
                    speed=0.5,
                    line_crossings=[
                        {
                            "line_id": "line-1",
                            "direction": "positive",
                            "frame_index": 2,
                        }
                    ],
                ),
            ],
        ),
        rules=[pedestrian_rule, congestion_rule, flow_rule],
        zones=[_zone("lane-1", "vehicle_lane")],
    )

    assert {event["event_type"] for event in first["events"]} == {"flow_counting"}
    assert {event["event_type"] for event in second["events"]} == {
        "pedestrian_in_vehicle_lane",
        "congestion",
    }
    flow_evidence = first["event_evidence"][0]["evidence_json"]
    assert flow_evidence["counting_line_id"] == "line-1"
    assert flow_evidence["direction"] == "positive"
    assert flow_evidence["track_id"] == 13
    assert flow_evidence["class_name"] == "car"
    assert all(event["event_type"] != "flow_counting" for event in second["events"])


def _frame(frame_index: int, trajectory_points: list[dict]) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": frame_index * 100,
        "trajectory_points": trajectory_points,
    }


def _point(
    *,
    track_id: int = 7,
    class_name: str = "car",
    zone_id: str = "lane-1",
    inside_frames: int = 3,
    speed: float = 2.0,
    moving_angle: float = 180.0,
    dwell_time_ms: int = 300,
    center_shift: float = 0.5,
    line_crossings: list[dict] | None = None,
) -> dict:
    zone_history = [
        {
            "zone_id": zone_id,
            "zone_type": "vehicle_lane",
            "first_seen_frame": 1,
            "last_seen_frame": inside_frames,
            "inside_frames": inside_frames,
            "inside_duration_ms": inside_frames * 100,
            "currently_inside": True,
        }
    ]
    return {
        "track_id": track_id,
        "class_name": class_name,
        "bbox": [0, 0, 10, 10],
        "center": [5, 5],
        "bottom_center": [5, 10],
        "speed_px_per_frame": speed,
        "moving_angle": moving_angle,
        "direction_consistency": 1.0,
        "dwell_time_ms": dwell_time_ms,
        "center_shift_px": center_shift,
        "zone_ids": [zone_id],
        "zone_history": zone_history,
        "lane_relation": {
            "current_vehicle_lane_ids": [zone_id],
            "person_in_vehicle_lane": class_name == "person",
            "vehicle_in_no_parking_zone": zone_id == "parking-1",
            "object_in_danger_zone": zone_id == "danger-1",
            "zone_membership": {zone_id: {"inside": True, "point_type": "bottom_center"}},
        },
        "line_crossings": line_crossings or [],
        "track_length": inside_frames,
    }


def _zone(zone_id: str, zone_type: str) -> dict:
    return {
        "zone_id": zone_id,
        "zone_type": zone_type,
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
    }
