"""Seed small SmartTraffic demo/sample configuration files.

The seed only writes human-readable config and expected annotation examples.
It never writes videos, model weights, analysis results, or eval result files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]


DEMO_ZONES: dict[str, Any] = {
    "schema_version": "stage9.demo.zones.v1",
    "description": "Toy zones for local dry-run demos. Coordinates are pixel-space examples.",
    "zones": [
        {
            "id": "zone_vehicle_lane_demo",
            "name": "Demo vehicle lane",
            "zone_type": "vehicle_lane",
            "polygon": [[80, 120], [560, 120], [620, 420], [40, 420]],
            "direction": {
                "start_point": [120, 360],
                "end_point": [520, 180],
                "allowed_angle": 335,
                "reverse_angle_threshold": 150,
            },
            "enabled": True,
            "video_id": "demo_video_local",
            "camera_id": "demo_camera_01",
        },
        {
            "id": "zone_danger_demo",
            "name": "Demo pedestrian danger zone",
            "zone_type": "danger_zone",
            "polygon": [[420, 210], [590, 210], [610, 380], [410, 380]],
            "enabled": True,
            "video_id": "demo_video_local",
            "camera_id": "demo_camera_01",
        },
        {
            "id": "zone_counting_line_demo",
            "name": "Demo counting line",
            "zone_type": "counting_line",
            "polygon": [[290, 90], [310, 90], [310, 440], [290, 440]],
            "counting_line": {
                "start_point": [300, 100],
                "end_point": [300, 430],
                "in_direction": "any",
                "enabled": True,
            },
            "enabled": True,
            "video_id": "demo_video_local",
            "camera_id": "demo_camera_01",
        },
    ],
}


DEMO_EVENT_RULES: dict[str, Any] = {
    "schema_version": "stage9.demo.rules.v1",
    "description": "Toy Event Engine rules for local dry-run demos.",
    "event_rules": [
        {
            "id": "rule_wrong_way_demo",
            "name": "Demo wrong-way driving",
            "event_type": "wrong_way_driving",
            "enabled": True,
            "zone_id": "zone_vehicle_lane_demo",
            "target_classes": ["car", "bus", "truck", "motorcycle"],
            "parameters": {
                "allowed_angle": 335,
                "angle_tolerance": 35,
                "min_speed_px_per_frame": 1.0,
            },
            "cooldown_seconds": 2.0,
            "severity": "high",
            "version": 1,
            "min_track_length": 2,
        },
        {
            "id": "rule_danger_zone_demo",
            "name": "Demo danger-zone intrusion",
            "event_type": "danger_zone_intrusion",
            "enabled": True,
            "zone_id": "zone_danger_demo",
            "target_classes": ["person", "bicycle", "motorcycle"],
            "parameters": {"min_dwell_frames": 1},
            "cooldown_seconds": 1.0,
            "severity": "critical",
            "version": 1,
            "min_track_length": 1,
        },
        {
            "id": "rule_flow_count_demo",
            "name": "Demo flow counting",
            "event_type": "flow_counting",
            "enabled": True,
            "zone_id": "zone_counting_line_demo",
            "target_classes": ["car", "bus", "truck", "motorcycle", "bicycle"],
            "parameters": {
                "line": [[300, 100], [300, 430]],
                "direction": "any",
                "count_once_per_track": True,
            },
            "cooldown_seconds": 0.0,
            "severity": "info",
            "version": 1,
            "min_track_length": 2,
        },
    ],
}


DEMO_PROCESSING_REQUEST: dict[str, Any] = {
    "schema_version": "stage9.demo.processing_request.v1",
    "description": "Toy process request body. Replace video_id in the URL with a locally uploaded video id.",
    "endpoint_template": "POST /api/videos/{video_id}/process",
    "body": {
        "mode": "detection_tracking_trajectory",
        "detector_dry_run": True,
        "tracker_dry_run": True,
        "frame_stride": 5,
        "max_frames": 30,
        "write_preview": False,
        "direction_window": 2,
        "dwell_speed_threshold": 1.0,
        "max_history_points": 20,
        "event_rules": DEMO_EVENT_RULES["event_rules"],
        "zones": DEMO_ZONES["zones"],
        "run_events": True,
        "generate_alerts": True,
        "record_not_matched": False,
    },
}


DEMO_EXPECTED_EVENTS: dict[str, Any] = {
    "schema_version": "stage9.demo.expected_events.v1",
    "dataset_id": "demo_toy_dataset",
    "description": "Tiny expected event examples for Evaluation MVP smoke input.",
    "events": [
        {
            "event_id": "expected_wrong_way_001",
            "event_type": "wrong_way_driving",
            "track_id": 101,
            "zone_id": "zone_vehicle_lane_demo",
            "start_frame": 10,
            "end_frame": 14,
            "severity": "high",
        },
        {
            "event_id": "expected_danger_zone_001",
            "event_type": "danger_zone_intrusion",
            "track_id": 202,
            "zone_id": "zone_danger_demo",
            "start_frame": 18,
            "end_frame": 20,
            "severity": "critical",
        },
        {
            "event_id": "expected_flow_count_001",
            "event_type": "flow_counting",
            "track_id": 303,
            "zone_id": "zone_counting_line_demo",
            "frame_index": 25,
            "severity": "info",
        },
    ],
}


DEMO_EXPECTED_COUNTS: dict[str, Any] = {
    "schema_version": "stage9.demo.expected_counts.v1",
    "dataset_id": "demo_toy_dataset",
    "description": "Tiny expected flow-count examples for Evaluation MVP smoke input.",
    "summary": {
        "total_count": 2,
        "vehicle_count": 2,
        "person_count": 0,
        "by_class": {"car": 1, "bus": 1},
        "by_direction": {"unknown": 2},
    },
    "records": [
        {
            "line_id": "zone_counting_line_demo",
            "class_name": "car",
            "direction": "unknown",
            "count": 1,
        },
        {
            "line_id": "zone_counting_line_demo",
            "class_name": "bus",
            "direction": "unknown",
            "count": 1,
        },
    ],
}


SEED_FILES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("samples/configs/demo_zones.json", DEMO_ZONES),
    ("samples/configs/demo_event_rules.json", DEMO_EVENT_RULES),
    ("samples/configs/demo_processing_request.json", DEMO_PROCESSING_REQUEST),
    ("evals/expected/demo_expected_events.json", DEMO_EXPECTED_EVENTS),
    ("evals/expected/demo_expected_counts.json", DEMO_EXPECTED_COUNTS),
)


def seed_demo_files(
    *,
    output_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "output_root": str(output_root),
        "created": [],
        "updated": [],
        "skipped": [],
        "would_create": [],
        "would_update": [],
    }
    for relative_path, payload in SEED_FILES:
        target = output_root / relative_path
        exists = target.exists()
        if dry_run:
            key = "would_update" if exists and force else "would_create"
            if exists and not force:
                summary["skipped"].append(relative_path)
            else:
                summary[key].append(relative_path)
            continue
        if exists and not force:
            summary["skipped"].append(relative_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        summary["updated" if exists else "created"].append(relative_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed small SmartTraffic demo/sample config files."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_DIR,
        help="Repository-like root to write under. Defaults to the project root.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing demo/sample files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be created or updated without writing.",
    )
    return parser


def print_summary(summary: dict[str, Any]) -> None:
    print(f"Demo seed root: {summary['output_root']}")
    for key, label in (
        ("created", "created"),
        ("updated", "updated"),
        ("skipped", "skipped"),
        ("would_create", "would create"),
        ("would_update", "would update"),
    ):
        values = summary[key]
        if values:
            print(f"{label}: {len(values)}")
            for value in values:
                print(f"  - {value}")
    if not any(summary[key] for key in ("created", "updated", "skipped", "would_create", "would_update")):
        print("No demo files selected.")
    print("No videos, model weights, generated results, or eval result files were written.")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    summary = seed_demo_files(
        output_root=args.output_root,
        force=args.force,
        dry_run=args.dry_run,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
