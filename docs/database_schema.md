# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
has a DB foundation, but remains primarily local-artifact based and does not
yet implement the full business database / repository layer.

本文是目标数据库设计，不代表当前仓库已经实现完整业务数据库层。

Current implementation notes:

- Full Stage 1AB has connected SQLAlchemy Declarative Base, engine/session
  dependency, Alembic baseline migration, and `SMARTTRAFFIC_DATABASE_URL`.
- The default local database URL is `sqlite:///./smarttraffic.db`.
- Videos and analysis runs may have local metadata or in-memory registry
  representation.
- Business SQLAlchemy models, repositories, migrations that create domain
  tables, and database-backed query services are not complete.
- `event_rules` and `zones` currently have artifact-based / in-memory MVP
  configuration APIs, not database-backed persistence.
- `review_comments`, `bad_cases`, `evaluation_datasets`, and
  `evaluation_results` now have artifact-backed MVP implementations. Their
  database tables remain target design, not completed DB-backed implementation.
- Event / alert results currently come from local artifacts under
  `results/traffic_analysis/<run_id>/`.

The schema target from the execution manual remains:

- `videos`
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

The current Alembic baseline is intentionally empty. Business table migrations
should be introduced when Full Stage 1CD moves the skeleton APIs toward
persisted state.
