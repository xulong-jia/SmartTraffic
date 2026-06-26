# Artifact Compatibility

Full Stage 1EF adds a compatibility layer between existing local run artifacts
and the new SQLAlchemy schema/repository foundation.

This is not a business API migration. Existing FastAPI endpoints continue to
use the artifact-backed MVP path unless a later stage explicitly wires them to
DB-backed services.

## Supported Artifacts

The compatibility layer discovers and can import structured run artifacts:

- `metadata.json`
- `manifest.json`
- `artifact_index.json`
- `detections.csv`
- `tracks.csv`
- `trajectory_points.csv`
- `events.jsonl`
- `alerts.jsonl`
- `flow_counts.json`
- `zone_statistics.json`
- `evaluation_summary.json`
- `bad_cases.jsonl`
- `bad_cases.csv`

It does not import videos, keyframe images, annotated videos, model weights, or
other binary assets. Those remain path references or local files outside Git.

## Import Behavior

`backend/app/analysis/artifact_compatibility.py` provides:

- artifact discovery for a single run directory
- dry-run import summaries
- idempotent artifact-to-DB import helpers
- DB-first / artifact-fallback read-through helpers

Repeated import skips records that already exist by stable IDs. Import keeps the
core fields needed for later migration stages and stores raw artifact payloads
where useful for compatibility.

## CLI

Preview an import without writing:

```bash
python3 scripts/import_artifacts_to_db.py --run-id <run_id> --result-dir results/traffic_analysis/<run_id>
```

Write to the configured database:

```bash
python3 scripts/import_artifacts_to_db.py --run-id <run_id> --result-dir results/traffic_analysis/<run_id> --write
```

Use a specific database URL:

```bash
python3 scripts/import_artifacts_to_db.py --run-id <run_id> --result-dir /path/to/run --database-url sqlite:////tmp/smarttraffic.db --write
```

The CLI intentionally works on one explicit run at a time. It does not scan the
entire results directory by default.

## Boundary

Full Stage 1 is now complete at the foundation level:

- Full Stage 1AB: SQLAlchemy / Alembic / Session / Config
- Full Stage 1CD: Core Models / Migrations / Repositories / CRUD Tests
- Full Stage 1EF: Artifact Compatibility / Import / Read-through

Still not complete:

- business API DB-backed migration
- Video / Processing DB-backed flow
- Event / Alert / Review / Bad Case / Evaluation DB-backed workflow
- frontend changes for DB-backed reads
- real evaluation metrics beyond the existing MVP artifacts
- realtime, permissions, production security, and reporting
