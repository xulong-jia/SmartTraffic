# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
has a DB foundation plus core SQLAlchemy models, migrations, repositories,
artifact compatibility helpers, and Stage 2AB DB-backed video / processing task
foundation. Most analytical detail reads remain local-artifact based.

本文描述当前 schema/repository foundation、Stage 2AB DB-backed 范围和目标数据库边界，不代表当前仓库已经完成 DB-backed 全量业务迁移。

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
- The default local database URL is `sqlite:///./smarttraffic.db`.
- Videos, processing tasks, and processing-created run indexes are DB-backed.
- Detection, tracking, trajectory, event, alert, flow count, zone statistic,
  review, bad case, and evaluation detail workflows have not been fully
  migrated to database-backed persistence.
- `event_rules` and `zones` currently have artifact-based / in-memory MVP
  configuration APIs, not database-backed persistence.
- `review_comments`, `bad_cases`, `evaluation_datasets`, and
  `evaluation_results` now have artifact-backed MVP implementations and schema
  foundation tables. Their business services are not yet DB-backed.
- Event / alert results currently come from local artifacts under
  `results/traffic_analysis/<run_id>/`.
- Full Stage 2CD and later stages are expected to continue Result Persistence
  and broader workflow migrations.

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
DB-backed processing lifecycle. Full Stage 1EF can import structured artifacts such as
`metadata.json`, `detections.csv`, `tracks.csv`, `trajectory_points.csv`,
`events.jsonl`, `alerts.jsonl`, `flow_counts.json`, `zone_statistics.json`,
`evaluation_summary.json`, and `bad_cases.jsonl` / `bad_cases.csv` into those
tables. Current analysis, review, bad-case, and evaluation detail endpoints
still use the artifact-backed MVP path; this is not the DB-backed full final
version.
