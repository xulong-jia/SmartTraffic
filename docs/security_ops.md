# Security / Ops Preview

Full Stage 7CD adds minimal local security and operations hardening for the
Realtime preview milestone. This is not production IAM.

## Minimal Actor Identity

APIs can read actor context from request headers:

- `X-SmartTraffic-Actor`
- `X-SmartTraffic-Role`

Supported roles:

- `viewer`
- `operator`
- `reviewer`
- `admin`

Missing headers default to `actor=system` and `role=operator` so existing local
API calls remain compatible.

## Auth Mode

`SMARTTRAFFIC_AUTH_MODE` controls enforcement:

- `permissive`: default. Actor is parsed and audit metadata is recorded, but
  permission failures do not block requests.
- `strict`: permission guard blocks disallowed writes.

Minimal strict-mode guard:

- `viewer`: read-only.
- `operator`: realtime start / stop, alert acknowledge / resolve / ignore,
  and config-style local operations.
- `reviewer`: review actions and Bad Case actions.
- `admin`: all preview permissions.

This is designed for local validation and future replacement by JWT/OAuth or an
enterprise identity provider.

## Audit Coverage

Stage 7CD records audit context without adding a new audit table:

- Review actions write actor into `review_comments.author` when request payload
  does not explicitly provide a reviewer.
- Alert acknowledge uses actor as `acknowledged_by` when the request body omits
  it.
- Rule rerun requests write actor into `processing_tasks.parameters.requested_by`.
- Realtime start writes actor and role into `processing_tasks.parameters`.
- Event status update writes actor into `events.payload.audit`.
- Bad Case create/update appends an `actor:<name>` tag.
- A structured audit logger emits `audit_event` lines with action, actor, role,
  resource type, resource id, and outcome.

## Error Handling

API errors include:

- `error_code`
- `message`
- `detail`
- `request_id`

Unhandled exceptions return a generic `internal_error` response and are logged
with request metadata. Error messages redact obvious secret / RTSP / password
content.

## Readiness

`GET /health` remains the lightweight liveness endpoint.

`GET /health/ready` checks:

- app alive
- database connectivity with a simple `SELECT 1`

Database failure returns HTTP `503` with `checks.database=error`.

## Stream URLs And Secrets

Camera responses expose `masked_stream_url`, not the full `stream_url`.
Repository policy remains:

- Do not commit `.env`.
- Do not commit real RTSP URLs.
- Do not commit secrets, tokens, passwords, or API keys.
- Do not commit `.db`, `.sqlite`, `.sqlite3`, generated realtime outputs,
  reports, results, local videos, model weights, cache, dist, or node_modules.

## Production Boundary

Production deployment still requires real authentication, authorization,
secret management, HTTPS termination, central audit storage, monitoring,
alerting, backup policy, migration policy, and runtime hardening. Report output
and realtime preview output are not traffic enforcement artifacts.
