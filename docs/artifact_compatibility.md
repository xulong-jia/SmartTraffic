# Artifact Compatibility

Full Stage 1EF adds a compatibility layer between existing local run artifacts
and the new SQLAlchemy schema/repository foundation.

This started as a foundation layer in Full Stage 1EF. Later stages now wire
selected FastAPI endpoints to DB-first behavior while preserving artifact
fallback for legacy runs.

## Supported Artifacts

The compatibility layer discovers and can import structured run artifacts:

- `metadata.json`
- `manifest.json`
- `artifact_index.json`
- `detections.csv`
- `tracks.csv`
- `trajectory_points.csv`
- `events.jsonl`
- `event_evidence.jsonl`
- `rule_executions.jsonl`
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

Event imports preserve `rule_id` and `zone_id` when present. Event evidence and
rule execution imports keep event/run/track/frame linkage in DB JSON payloads so
Review, Bad Case, and Evaluation flows can trace why an event was emitted.

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

Full Stage 1 is complete at the foundation level:

- Full Stage 1AB: SQLAlchemy / Alembic / Session / Config
- Full Stage 1CD: Core Models / Migrations / Repositories / CRUD Tests
- Full Stage 1EF: Artifact Compatibility / Import / Read-through

Later DB-backed core-flow stages now complete:

- Full Stage 2AB: Video / Processing DB-backed flow
- Full Stage 2CD: Core result persistence and Analysis Runs DB-first reads
- Full Stage 3AB: Zone / Rule config and top-level Event API DB flow
- Full Stage 3CD: Event / Alert / Review DB lifecycle
- Full Stage 3EF: Bad Case / Evaluation DB workflow, including failed cases in
  `evaluation_results.summary["failed_cases"]`

Still not complete after Full Stage 7CD / 8AB audit:

- full final production-grade DB-backed version
- COCO official mAP
- TrackEval official IDF1 / MOTA
- complete video-level Bad Case rerun pipeline
- production realtime monitoring
- production IAM, central audit storage, and deployment hardening
