# SmartTraffic Reporting

Full Stage 6AB adds Report Center CSV / JSON export for local analysis and
review workflows.

## API

- `GET /api/reports/runs`
- `GET /api/reports/{run_id}/summary`
- `GET /api/reports/{run_id}/export.json`
- `GET /api/reports/{run_id}/export.csv?section=<section>`

Supported CSV sections:

- `events`
- `alerts`
- `flow_counts`
- `zone_statistics`
- `bad_cases`
- `evaluation_results`

## Frontend

The React Report Center is available from the sidebar at `/reports`. It lets
users choose an analysis run, inspect report summary cards, download one CSV
section, and preview/download the structured JSON report.

## Boundaries

Reports are for analysis and review only, not traffic enforcement. Full Stage
6AB does not generate PDF reports, MP4 / annotated video exports, keyframe
summary packages, realtime reports, or permission-protected report workflows.
Generated report files remain local browser downloads and must not be committed.
