from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "scripts"))

from danger_check import find_blocked_files  # noqa: E402


def test_danger_check_ignores_local_generated_asset_directories(tmp_path: Path) -> None:
    for directory_name in ["results", "local_videos", "local_models", "frontend/dist"]:
        directory = tmp_path / directory_name
        directory.mkdir(parents=True)
        (directory / "generated.mp4").write_bytes(b"video")
        (directory / "model.pt").write_bytes(b"weights")

    (tmp_path / "unexpected.mp4").write_bytes(b"video")

    matches = {path.relative_to(tmp_path).as_posix() for path in find_blocked_files(tmp_path)}

    assert matches == {"unexpected.mp4"}
