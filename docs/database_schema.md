# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
has a DB foundation plus core SQLAlchemy models, migrations, repositories,
artifact compatibility helpers, Stage 2AB DB-backed video / processing task
foundation, Stage 2CD DB-backed core result persistence, Stage 3AB DB-backed
config / event API flow, Stage 3CD DB-backed event / alert / review lifecycle
foundation, and Stage 3EF DB-backed Bad Case / Evaluation workflow foundation.

本文描述当前 schema/repository foundation、Full Stage 2 DB-backed 核心流、Full Stage 3AB config / event API、Full Stage 3CD event / alert / review、Full Stage 3EF Bad Case / Evaluation 范围和目标数据库边界，不代表当前仓库已经完成 DB-backed 全量业务迁移。

Current implementation notes:

- Full Stage 1AB has connected SQLAlchemy Declarative Base, engine/session
  dependency, Alembic baseline migration, and `SMARTTRAFFIC_DATABASE_URL`.
- Full Stage 1CD has added core SQLAlchemy models, a business-table Alembic
  migration, repository classes, and CRUD tests.
- Full Stage 1EF has added artifact discovery, artifact-to-DB import helpers,
  DB-first / artifact-fallback read-through helpers, and a dry-run-by-default
  import CLI.
- Full Stage 2AB has migrated video upload/list/detail/status/frames and
  processing task lifecycle state to the DB. Processing now writes
  `processing_tasks` and `traffic_analysis_runs` rows while preserving local
  video files and local run artifacts.
- Full Stage 2CD has added DB persistence for `detections`, `tracks`,
  `trajectory_points`, `flow_counts`, and `zone_statistics`. Analysis Runs core
  endpoints now read DB first and fall back to artifacts when DB rows are
  missing.
- Full Stage 3AB has migrated `zones` and `event_rules` API CRUD to DB-backed
  services, added version-aware response mapping, stores run-level
  zone/rule config snapshots in `traffic_analysis_runs.summary`, and adds
  top-level Event APIs with DB-first reads plus artifact fallback.
- Full Stage 3CD has added a DB event lifecycle service for `events`,
  `event_evidence`, and `rule_executions`, DB-first `/api/analysis-runs/{run_id}/events`
  read-through, DB-first Alert Center status transitions, Review workflow audit
  records in `review_comments`, false-negative event records, and
  `processing_tasks.mode=rule_rerun` request rows.
- Full Stage 3EF has added DB-first Bad Case workflow over `bad_cases`, DB-first
  Evaluation dataset/result workflow over `evaluation_datasets` and
  `evaluation_results`, failed cases persisted in
  `evaluation_results.summary["failed_cases"]`, and optional CLI DB writes via
  `scripts/run_evals.py --write-db`.
- The default local database URL is `sqlite:///./smarttraffic.db`.
- Videos, processing tasks, processing-created run indexes, detections, tracks,
  trajectory points, flow counts, zone statistics, zones, event rules,
  top-level event reads/status updates, event evidence, rule executions, alert
  status transitions, review audit records, Bad Case workflow, Evaluation
  dataset/result workflow, and failed-case conversion are DB-backed.
- `event_rules` and `zones` now use DB-backed CRUD APIs. The frontend
  ZoneEditor has not been redesigned in this stage.
- `review_comments` now stores DB-backed Review action audit records for DB
  events. `bad_cases`, `evaluation_datasets`, and `evaluation_results` now have
  DB-first API workflows while preserving artifact fallback.
- Event / alert artifacts still come from local artifacts under
  `results/traffic_analysis/<run_id>/` for legacy and artifact-only runs.
- Full Stage 3 and later stages are expected to continue Event / Alert, Review,
  Bad Case, Evaluation, and broader workflow migrations.

The schema target from the execution manual remains:

- `videos`
- `cameras`
- `frames`
- `detections`
- `tracks`
- `trajectory_points`
- `events`
- `event_evidence`
- `alerts`
- `event_rules`
- `zones`
- `flow_counts`
- `zone_statistics`
- `processing_tasks`
- `traffic_analysis_runs`
- `rule_executions`
- `review_comments`
- `bad_cases`
- `evaluation_datasets`
- `evaluation_results`
- `model_runs`

Full Stage 1CD creates these tables through Alembic and provides repository
CRUD helpers. Full Stage 2AB adds `processing_tasks.progress`,
`processing_tasks.started_at`, and `processing_tasks.finished_at` for the
DB-backed processing lifecycle. Full Stage 2CD writes the generated core result
artifacts into the corresponding DB tables after processing succeeds. Full
Stage 3CD persists event evidence, rule execution rows, alert status changes,
review audit comments, false-negative event records, and rule rerun request
tasks while preserving artifact fallback. Full Stage 3EF persists Bad Case
records in `bad_cases`, Evaluation dataset records in `evaluation_datasets`,
Evaluation metric results in `evaluation_results.metrics`, and run summary /
failed cases in `evaluation_results.summary`. Full Stage 1EF can import structured
artifacts such as
`metadata.json`, `detections.csv`, `tracks.csv`, `trajectory_points.csv`,
`events.jsonl`, `alerts.jsonl`, `flow_counts.json`, `zone_statistics.json`,
`evaluation_summary.json`, and `bad_cases.jsonl` / `bad_cases.csv` into those
tables. Full Stage 3AB stores zone/rule config snapshots inside
`traffic_analysis_runs.summary["event_config_snapshot"]` without adding a new
table. Current real mAP / IDF1 / MOTA and real rerun-based Bad Case regression
are still outside this schema workflow and remain Full Stage 4 work; this is
not the DB-backed full final version.
