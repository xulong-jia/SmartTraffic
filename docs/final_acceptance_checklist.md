# SmartTraffic Full Final Acceptance Checklist

## 1. Version Baseline

- Current pre-final baseline: `v0.9.7-realtime-security-preview`.
- Full Stage 8AB prepares final audit documentation only.
- Do not create `v1.0.0-full-final-version` until Full Stage 8CD final
  acceptance is complete.
- `v1.0.0-full-final-version` is frozen after final acceptance. The
  `v1.0.1-audit-polish` milestone is a scoped audit polish tag, not a new
  production capability release, and must not move or rebuild any `v1.0.0`
  tag.
- `v1.0.2-spec-alignment` is a scoped spec-alignment patch after v1.0.1. It
  must not move or rebuild `v1.0.1-audit-polish` or
  `v1.0.0-full-final-version`.
- `v1.0.3-final-hardening` is a scoped final hardening patch after v1.0.2. It
  must not move or rebuild `v1.0.2-spec-alignment`,
  `v1.0.1-audit-polish`, or `v1.0.0-full-final-version`.
- Existing milestone tags must not be moved, deleted, or rebuilt.

## 2. Functional Acceptance

- Video upload, metadata extraction, processing tasks, and per-video run index
  are DB-backed for local validation.
- Detection, tracking, trajectory, event, alert, review, Bad Case, Evaluation,
  report, camera, and realtime preview APIs are available within their stated
  boundaries.
- Frontend workflows cover Dashboard, Video Center, Analysis Detail with
  overlays, Alert Center, Review Center, Bad Case Center, Evaluation Center,
  Report Center, ZoneEditor, and Camera Center.
- `v1.0.1-audit-polish` removes the last frontend contract-only audit gaps:
  `AlertPanel` and `EventTable` are real reusable components connected to
  Alert Center and Analysis Detail respectively.
- `v1.0.3-final-hardening` validates video upload extension, size, OpenCV
  metadata duration, and OpenCV FOURCC / codec allowlist, with clear client
  errors and no traceback or local path leakage.

## 3. Engineering Acceptance

- FastAPI backend, React/Vite frontend, SQLAlchemy session layer, Alembic
  migrations, Docker Compose config, Makefile checks, and local danger checks
  must pass before final tagging.
- API error responses include stable `error_code`, `message`, `detail`, and
  `request_id` fields.
- Request logging and DB readiness are available for local ops validation.

## 4. Database Acceptance

- Alembic migrations cover videos, cameras, frames, processing tasks,
  analysis runs, model runs, detections, tracks, trajectory points, flow
  counts, zone statistics, zones, event rules, events, event evidence, rule
  executions, alerts, review comments, bad cases, evaluation datasets, and
  evaluation results.
- Current default database is local SQLite for prototype validation.
- `frames` are accepted as a metadata / query contract, and `tracks` are
  accepted as run-level track records plus metadata / artifact-compatible rows;
  the current prototype does not claim a production normalized per-frame
  tracking table.
- Do not claim PostgreSQL production deployment or production migration
  operations are complete.

## 5. Detection / Tracking Acceptance

- YOLOv8 adapter and deterministic dry-run detection are available.
- DeepSORT adapter and deterministic mock tracker are available.
- Detection metrics are VOC-style single-IoU AP/mAP with precision, recall,
  and per-class AP when annotations exist.
- Tracking metrics are lightweight deterministic IDF1 / MOTA / ID switch /
  track-lost calculations.
- Detection mAP is not COCO official mAP.
- Tracking IDF1 / MOTA are not TrackEval official implementation.

## 6. Trajectory / Event Acceptance

- TrajectoryEngine emits center, speed, direction vector, moving angle,
  dwell time, zone history, lane relation, line crossings, track length, and
  last-seen features.
- Event Engine supports wrong-way, illegal parking, danger-zone intrusion,
  pedestrian lane intrusion, congestion, and flow counting.
- Event evidence and rule execution records are persisted or artifact-backed
  according to run availability.
- Pixel speed and direction are not real-world calibrated values.

## 7. Traffic Analysis / Alert / Review Acceptance

- Traffic Analysis Center run list, summary, manifest, detections, tracks,
  trajectory points, events, alerts, flow counts, and zone statistics are
  DB-first with artifact fallback where applicable.
- `GET /api/analysis-runs/{run_id}/alerts` is DB-first for DB `alerts` rows and
  preserves artifact fallback when no DB alert rows exist.
- Event rule severity is backend-validated as `low` / `medium` / `high`;
  Alert Center `level` is a separate alert concept and may be `info` /
  `warning` / `critical`.
- `/api/processing/tasks` is DB-backed and supports local visibility filters
  for `video_id`, `run_id`, `status`, `mode`, and `task_type`.
- Alert Center supports `new`, `acknowledged`, `resolved`, and `ignored`.
- Review Center supports confirm, false positive, false negative, ignore,
  resolve, comments, Review -> Bad Case, and rule-rerun request recording.
- Review actions do not automatically become enforcement decisions.

## 8. Bad Case / Evaluation Acceptance

- Bad Case CRUD, filtering, summary, from-review, and from-failed-case flows
  are DB-first with artifact fallback.
- Evaluation datasets, results, failed cases, and regression summaries are
  DB-first with artifact fallback.
- DB-backed processing writes detector/tracker business records into
  `model_runs` with sanitized path/config parameters, summary metrics, and
  artifact references.
- Bad Case regression is deterministic replay / stored rule replay.
- Regression is not a complete video pipeline rerun.

## 9. Report / Realtime / Security Acceptance

- Report Center supports CSV, JSON, PDF export, report bundle metadata,
  keyframe summary, and annotated video references.
- Reports are for analysis and review only, not traffic enforcement.
- Realtime is a preview with mock, local file smoke, upload placeholder, and
  RTSP no-connect behavior.
- Realtime preview is not production realtime monitoring.
- Security uses minimal actor identity with permissive / strict modes.
- Minimal actor identity is not production IAM.

## 10. Safety / Data / Git Acceptance

- Do not commit `.env`, secrets, real RTSP URLs, local DB files, generated
  reports, generated results, videos, model weights, caches, `dist`, or
  `node_modules`.
- `backend/smarttraffic.db`, `.sqlite`, `.sqlite3`, `.db`, `__pycache__`, and
  `*.pyc` must remain untracked.
- Final release checks must include backend tests, frontend tests/build,
  compile checks, Docker config, danger check, large-file scan, secret scan,
  RTSP scan, and tracked-forbidden-file scan.

## 11. Remaining Boundaries

- SmartTraffic is not a formal traffic enforcement system.
- SmartTraffic is not production IAM.
- Realtime preview is not production realtime monitoring.
- Detection mAP is VOC-style single-IoU, not COCO official.
- IDF1 / MOTA are lightweight deterministic metrics, not TrackEval official.
- Regression is deterministic replay / stored rule replay, not full video
  pipeline rerun.
- These are intentional design boundaries, not unresolved Stage 8AB bugs.
