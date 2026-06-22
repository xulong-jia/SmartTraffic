from pathlib import Path


def run_directory(base_dir: str | Path, run_id: str) -> Path:
    return Path(base_dir) / run_id
