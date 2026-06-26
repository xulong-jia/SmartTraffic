#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import one SmartTraffic run's structured artifacts into the configured database.",
    )
    parser.add_argument("--run-id", required=True, help="Run id to import.")
    parser.add_argument(
        "--result-dir",
        required=True,
        help="Path to the run result directory, or a root containing the run directory.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy database URL. Defaults to SMARTTRAFFIC_DATABASE_URL or local SQLite config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Plan the import without writing. This is the default.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write records to the database. Without this flag the command is dry-run only.",
    )
    args = parser.parse_args()
    dry_run = not args.write

    import app.models  # noqa: F401
    from app.analysis.artifact_compatibility import import_run_artifacts_to_db
    from app.db.session import get_sessionmaker

    SessionLocal = get_sessionmaker(database_url=args.database_url)
    with SessionLocal() as session:
        summary = import_run_artifacts_to_db(
            session,
            args.run_id,
            args.result_dir,
            dry_run=dry_run,
        )
        if not dry_run:
            session.commit()
        print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
