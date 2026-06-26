# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
has a DB foundation plus core SQLAlchemy models, migrations, and repositories,
plus artifact compatibility helpers, but remains primarily local-artifact based
at the business API/service layer.

本文描述当前 schema/repository foundation 和目标数据库边界，不代表当前仓库已经完成 DB-backed 业务迁移。

Current implementation notes:

- Full Stage 1AB has connected SQLAlchemy Declarative Base, engine/session
  dependency, Alembic baseline migration, and `SMARTTRAFFIC_DATABASE_URL`.
- Full Stage 1CD has added core SQLAlchemy models, a business-table Alembic
  migration, repository classes, and CRUD tests.
- Full Stage 1EF has added artifact discovery, artifact-to-DB import helpers,
  DB-first / artifact-fallback read-through helpers, and a dry-run-by-default
  import CLI.
- The default local database URL is `sqlite:///./smarttraffic.db`.
- Videos and analysis runs may have local metadata or in-memory registry
  representation.
- Business API/services have not been migrated to database-backed persistence.
- `event_rules` and `zones` currently have artifact-based / in-memory MVP
  configuration APIs, not database-backed persistence.
- `review_comments`, `bad_cases`, `evaluation_datasets`, and
  `evaluation_results` now have artifact-backed MVP implementations and schema
  foundation tables. Their business services are not yet DB-backed.
- Event / alert results currently come from local artifacts under
  `results/traffic_analysis/<run_id>/`.
- Full Stage 2 is expected to start Video / Processing / Result Persistence
  business migration.

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
CRUD helpers. Full Stage 1EF can import structured artifacts such as
`metadata.json`, `detections.csv`, `tracks.csv`, `trajectory_points.csv`,
`events.jsonl`, `alerts.jsonl`, `flow_counts.json`, `zone_statistics.json`,
`evaluation_summary.json`, and `bad_cases.jsonl` / `bad_cases.csv` into those
tables. Current API endpoints still use the artifact-backed MVP path; this is
not the DB-backed full final version.
