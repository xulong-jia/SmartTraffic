import json
from pathlib import Path

from app.analysis.artifact_writer import TrafficArtifactWriter


def test_artifact_writer_creates_run_directory_and_metadata(tmp_path: Path) -> None:
    writer = TrafficArtifactWriter(base_dir=tmp_path)

    run_dir = writer.create_run_directory(
        run_id="run_001",
        metadata={
            "video_id": "video_001",
            "detector_config": {"confidence_threshold": 0.25},
        },
    )

    metadata_path = run_dir / "metadata.json"
    assert run_dir == tmp_path / "run_001"
    assert metadata_path.is_file()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run_001"
    assert metadata["video_id"] == "video_001"
    assert metadata["artifacts"]["detections"] == "detections.csv"
    assert (run_dir / "keyframes").is_dir()
