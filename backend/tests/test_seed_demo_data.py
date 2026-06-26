import importlib.util
import json
from pathlib import Path


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
    assert len(payload["zones"]) == 3
