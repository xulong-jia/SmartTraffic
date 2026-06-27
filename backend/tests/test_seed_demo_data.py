import importlib.util
import json
from pathlib import Path

from app.analysis.evaluation_metrics import compute_event_metrics
from app.events.engine import EventEngine
from app.events.rules import EventRule
from app.schemas.event_rule import EventRuleCreate
from app.schemas.processing import DetectionProcessRequest
from app.schemas.zone import ZoneCreate
from app.services.event_rule_service import event_rule_service
from app.trajectory.engine import TrajectoryEngine


PROJECT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "seed_demo_data.py"


def load_seed_module():
    spec = importlib.util.spec_from_file_location("seed_demo_data", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_seed_demo_data_dry_run_does_not_write(tmp_path, capsys):
    module = load_seed_module()

    module.main(["--dry-run", "--output-root", str(tmp_path)])

    output = capsys.readouterr().out
    assert "would create: 5" in output
    assert not (tmp_path / "samples" / "configs" / "demo_zones.json").exists()
    assert not (tmp_path / "evals" / "expected" / "demo_expected_events.json").exists()


def test_seed_demo_data_writes_json_to_output_root(tmp_path):
    module = load_seed_module()

    summary = module.seed_demo_files(output_root=tmp_path)

    assert len(summary["created"]) == 5
    assert not summary["updated"]
    for relative_path in summary["created"]:
        payload = json.loads((tmp_path / relative_path).read_text(encoding="utf-8"))
        assert payload["schema_version"].startswith("stage9.demo.")
    processing_request = json.loads(
        (tmp_path / "samples" / "configs" / "demo_processing_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert processing_request["body"]["detector_dry_run"] is True
    assert processing_request["body"]["tracker_dry_run"] is True
    assert processing_request["body"]["run_events"] is True
    assert len(processing_request["body"]["event_rules"]) == 6
    expected_events = json.loads(
        (tmp_path / "evals" / "expected" / "demo_expected_events.json").read_text(
            encoding="utf-8"
        )
    )
    assert {
        event["event_type"] for event in expected_events["events"]
    } == {
        "wrong_way_driving",
        "danger_zone_intrusion",
        "flow_counting",
        "illegal_parking",
        "pedestrian_in_vehicle_lane",
        "congestion",
    }


def test_seed_demo_data_does_not_overwrite_without_force(tmp_path):
    module = load_seed_module()
    target = tmp_path / "samples" / "configs" / "demo_zones.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"schema_version":"custom"}\n', encoding="utf-8")

    summary = module.seed_demo_files(output_root=tmp_path)

    assert "samples/configs/demo_zones.json" in summary["skipped"]
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "custom"


def test_seed_demo_data_force_overwrites_existing_file(tmp_path):
    module = load_seed_module()
    target = tmp_path / "samples" / "configs" / "demo_zones.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"schema_version":"custom"}\n', encoding="utf-8")

    summary = module.seed_demo_files(output_root=tmp_path, force=True)

    assert "samples/configs/demo_zones.json" in summary["updated"]
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "stage9.demo.zones.v1"
    assert len(payload["zones"]) == 4


def test_demo_expected_events_match_synthetic_actuals_for_six_types():
    module = load_seed_module()
    expected_events = module.DEMO_EXPECTED_EVENTS["events"]
    actual_events = [
        {**event, "event_id": event["event_id"].replace("expected", "actual")}
        for event in expected_events
    ]

    metrics = compute_event_metrics(
        expected_events=expected_events,
        actual_events=actual_events,
        frame_tolerance=0,
    )

    assert metrics["event_count_expected"] == 6
    assert metrics["true_positive"] == 6
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["failed_cases"] == []


def test_demo_processing_request_matches_backend_contract():
    payload = json.loads(
        (PROJECT_DIR / "samples" / "configs" / "demo_processing_request.json").read_text(
            encoding="utf-8"
        )
    )["body"]

    request = DetectionProcessRequest(**payload)
    assert request.event_rules is not None
    assert request.zones is not None
    assert {rule["severity"] for rule in request.event_rules} <= {"low", "medium", "high"}
    assert {zone["zone_type"] for zone in request.zones} >= {"counting_zone"}

    for rule in request.event_rules:
        EventRuleCreate(**rule)
        EventRule.from_dict(rule)
    for zone in request.zones:
        ZoneCreate(**zone)


def test_demo_counting_zone_drives_line_crossing_and_flow_event():
    payload = json.loads(
        (PROJECT_DIR / "samples" / "configs" / "demo_processing_request.json").read_text(
            encoding="utf-8"
        )
    )["body"]
    config = event_rule_service.build_event_engine_config(
        zones=payload["zones"],
        rules=payload["event_rules"],
    )
    engine = TrajectoryEngine()
    first = engine.update(
        _trajectory_frame(1, [260, 200, 280, 240]),
        zones=config["zones"],
    )
    second = engine.update(
        _trajectory_frame(2, [320, 200, 340, 240]),
        zones=config["zones"],
    )

    crossing = second["trajectory_points"][0]["line_crossings"][0]
    assert crossing["line_id"] == "zone_counting_line_demo"
    result = EventEngine(run_id="demo-run", video_id="demo-video").evaluate(
        [first, second],
        rules=config["event_rules"],
        zones=config["zones"],
    )
    assert "flow_counting" in {event["event_type"] for event in result["events"]}


def _trajectory_frame(frame_index: int, bbox: list[float]) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": frame_index * 100,
        "tracks": [
            {
                "track_id": 303,
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.9,
                "bbox": bbox,
                "state": "confirmed",
            }
        ],
    }
