# SmartTraffic Reporting

Full Stage 6AB/6CD adds Report Center CSV / JSON / PDF export and report bundle
metadata for local analysis and review workflows.

## API

- `GET /api/reports/runs`
- `GET /api/reports/{run_id}/summary`
- `GET /api/reports/{run_id}/bundle`
- `GET /api/reports/{run_id}/export.json`
- `GET /api/reports/{run_id}/export.csv?section=<section>`
- `GET /api/reports/{run_id}/export.pdf`

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
section, preview/download the structured JSON report, download the lightweight
PDF report, and inspect bundle / visual artifact metadata.

## Bundle And Visual Artifacts

The bundle endpoint returns metadata only. It lists included report sections,
relative artifact references, keyframe index status, keyframe item references,
and annotated video reference status. It does not build a zip file, copy an
MP4, read keyframe image bytes, or generate new visual artifacts.

## Boundaries

Reports are for analysis and review only, not traffic enforcement. PDF exports
include this disclaimer and are generated in memory for browser download. Full
Stage 6CD does not generate new MP4 / annotated video files, embed keyframe
images, create report zip bundles, implement realtime reports, or add
permission-protected report workflows. Generated report files remain local
browser downloads and must not be committed.
