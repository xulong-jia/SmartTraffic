# API Reference

## Health

- `GET /health`
- `GET /api/config`

## Videos

- `POST /api/videos/upload`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `POST /api/videos/{video_id}/process`
- `GET /api/videos/{video_id}/status`

`POST /api/videos/{video_id}/process` supports:

- `mode=detection_only`
- `mode=detection_tracking`
- `detector_dry_run`
- `tracker_dry_run`
- `frame_stride`
- `max_frames`
- `conf_threshold`
- `iou_threshold`
- `write_preview`

## Analysis Runs

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/detections?limit=100`
- `GET /api/analysis-runs/{run_id}/tracks?limit=100`

## Placeholders For Later Phases

- `GET /api/detections`
- `GET /api/tracks`
- `GET /api/trajectories`
- `GET /api/events`
- `GET /api/alerts`
- `GET /api/zones`
- `GET /api/review/events`
- `GET /api/bad-cases`
- `GET /api/evaluation/results`

These placeholder endpoints exist to preserve module boundaries. Full trajectory, event, alert, review, bad-case, and evaluation behavior belongs to later phases.
