# Database Schema

This document describes the target database schema from
`docs/SmartTraffic_最终版项目开发执行手册.md`. The current project implementation
is still primarily local-artifact based and does not yet implement the full
database / repository / migration layer.

本文是目标数据库设计，不代表当前仓库已经实现完整数据库层。

Current implementation notes:

- Videos and analysis runs may have local metadata or in-memory registry
  representation.
- Full SQLAlchemy models, repositories, migrations, and database-backed query
  services are not complete.
- `event_rules`, `zones`, `review_comments`, `bad_cases`,
  `evaluation_datasets`, and `evaluation_results` are target design, not
  completed implementation.
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

Database migrations should be introduced when phase one moves from skeleton APIs to persisted state.
