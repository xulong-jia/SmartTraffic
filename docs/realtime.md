# Realtime Preview

Full Stage 7AB provides a lightweight realtime preview layer for local
validation. It is not production realtime monitoring.

## Scope

Implemented:

- DB-backed Cameras API.
- Camera `source_type`: `upload`, `rtsp`, `file`, `mock`.
- Camera enable / disable.
- Default responses mask `stream_url` as `masked_stream_url`.
- Realtime preview start / stop / status APIs.
- Mock stream preview with deterministic frame metadata, event, and alert.
- Local file smoke-level preview.
- RTSP no-connect preview; no real RTSP dependency.
- Recent frame / event / alert cache, bounded to 20 items per camera.
- `processing_tasks.mode=realtime_process` record created on start.
- Camera Center frontend page for minimal operations.

Not implemented in Stage 7AB:

- Production realtime streaming.
- Real RTSP decoding or reconnect handling.
- Celery, distributed queues, or long-running worker orchestration.
- Authentication, permissions, multi-user audit, or ops hardening.
- Persistent frame image outputs or realtime video artifacts.

## APIs

Cameras:

- `POST /api/cameras`
- `GET /api/cameras`
- `GET /api/cameras/{camera_id}`
- `PATCH /api/cameras/{camera_id}`
- `DELETE /api/cameras/{camera_id}`
- `POST /api/cameras/{camera_id}/enable`
- `POST /api/cameras/{camera_id}/disable`

Realtime preview:

- `POST /api/realtime/{camera_id}/start`
- `POST /api/realtime/{camera_id}/stop`
- `GET /api/realtime/{camera_id}/status`
- `GET /api/realtime/{camera_id}/recent-frames`
- `GET /api/realtime/{camera_id}/recent-events`
- `GET /api/realtime/{camera_id}/recent-alerts`

## Security Boundary

`stream_url` is stored for local configuration but is not returned in normal
camera responses. Responses expose only `masked_stream_url`. Tests use mock
URLs and local placeholder files. Do not commit real RTSP URLs, credentials,
local video paths, `.db` / `.sqlite` files, generated realtime outputs, model
weights, or cache/build directories.

Security, permissions, audit trails, production error handling, observability,
deployment hardening, and the `v0.9.7-realtime-security-preview` tag
preparation are left for Full Stage 7CD.
