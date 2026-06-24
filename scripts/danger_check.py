from pathlib import Path


BLOCKED_SUFFIXES = {".pt", ".pth", ".onnx", ".engine", ".mp4", ".avi", ".mov", ".mkv", ".webm"}
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "local_models",
    "local_videos",
    "node_modules",
    "results",
}


def find_blocked_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("*"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in BLOCKED_SUFFIXES:
            matches.append(path)
    return matches


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    matches = find_blocked_files(root)
    for path in matches:
        print(path.relative_to(root))
    if matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
