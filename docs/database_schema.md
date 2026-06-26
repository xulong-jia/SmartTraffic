# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
has a DB foundation plus core SQLAlchemy models, migrations, repositories,
artifact compatibility helpers, Stage 2AB DB-backed video / processing task
foundation, Stage 2CD DB-backed core result persistence, and Stage 3AB
DB-backed config / event API flow.

本文描述当前 schema/repository foundation、Full Stage 2 DB-backed 核心流、Full Stage 3AB config / event API 范围和目标数据库边界，不代表当前仓库已经完成 DB-backed 全量业务迁移。

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
- The default local database URL is `sqlite:///./smarttraffic.db`.
- Videos, processing tasks, processing-created run indexes, detections, tracks,
  trajectory points, flow counts, zone statistics, zones, event rules, and
  top-level event reads/status updates are DB-backed.
- Event / Alert lifecycle, review, bad case, and evaluation workflows have not
  been fully migrated to database-backed persistence.
- `event_rules` and `zones` now use DB-backed CRUD APIs. The frontend
  ZoneEditor has not been redesigned in this stage.
- `review_comments`, `bad_cases`, `evaluation_datasets`, and
  `evaluation_results` now have artifact-backed MVP implementations and schema
  foundation tables. Their business services are not yet DB-backed.
- Event / alert results currently come from local artifacts under
  `results/traffic_analysis/<run_id>/`.
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
Stage 1EF can import structured artifacts such as
`metadata.json`, `detections.csv`, `tracks.csv`, `trajectory_points.csv`,
`events.jsonl`, `alerts.jsonl`, `flow_counts.json`, `zone_statistics.json`,
`evaluation_summary.json`, and `bad_cases.jsonl` / `bad_cases.csv` into those
tables. Full Stage 3AB stores zone/rule config snapshots inside
`traffic_analysis_runs.summary["event_config_snapshot"]` without adding a new
table. Current Alert lifecycle, Review audit trail, Bad Case full workflow, and
Evaluation workflow endpoints still use artifact-backed MVP paths or minimal DB
linkage; this is not the DB-backed full final version.
