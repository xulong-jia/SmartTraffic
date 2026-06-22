# Database Schema

Phase one uses in-memory registries and local files only. The schema target from the execution manual remains:

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
