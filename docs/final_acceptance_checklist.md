# SmartTraffic Final Delivery Acceptance Checklist

## 1. Current Scope

- The current `main` branch is the final local validation and demo delivery
  line.
- Current final tag: `v1.0.1-spec-completion`.
- Current final baseline: SmartTraffic `v1.0.1-spec-completion`, the
  spec-complete final local delivery baseline.
- `v1.0.0-smarttraffic-final-local-delivery` and `v1.0.3-final-hardening`
  remain preserved historical local delivery / hardening tags. They must not
  be moved, deleted, rebuilt, or retagged.
- The eight core completion areas passed within the local delivery / local
  validation scope: trajectory, zone/rule config, event engine, traffic
  analysis, dashboard/alerts, review/bad case, evaluation, and Docker delivery.
- This checklist is for local prototype acceptance, not production deployment,
  traffic enforcement, production IAM, calibrated traffic engineering, or
  commercial operations.

## 2. Docker Local Delivery

- `docker compose config` must pass.
- `docker compose build` should pass when the local Docker daemon and external
  image registry access are available.
- Backend container startup must run Alembic migrations before FastAPI.
- Frontend service must run the Vite dev server against
  `VITE_API_BASE_URL=http://localhost:8000`.
- Compose must mount `local_videos/`, `local_models/`, `results/`, `evals/`,
  and read-only `samples/` without committing their generated or heavy
  contents.
- `.env.example` is safe to commit. Local `.env` overrides remain untracked.

## 3. Functional Acceptance

- Video upload, metadata extraction, processing tasks, and per-video run index
  are DB-backed for local validation.
- Detection, tracking, trajectory, event, alert, review, Bad Case, Evaluation,
  report, camera, and realtime preview APIs are available within their stated
  boundaries.
- Frontend workflows cover Dashboard, Video Center, Analysis Detail, Alert
  Center, Review Center, Bad Case Center, Evaluation Center, Report Center,
  ZoneEditor, and Camera Center.
- Event evidence and rule execution records are persisted when DB-backed runs
  are available and remain artifact-compatible for legacy runs.

## 4. Demo Acceptance

- `scripts/seed_demo_data.py` creates only small JSON config and toy expected
  annotations.
- Current demo sample includes four zones, six event rules, six expected event
  examples, and two expected flow-count examples.
- Demo seed validation must pass:

```bash
./backend/.venv/bin/python -m pytest backend/tests/test_seed_demo_data.py -q
```

- No demo command should write real videos, model weights, generated run
  results, or evaluation result artifacts into Git-tracked paths.

## 5. Safety / Data / Git Acceptance

- Do not commit `.env`, secrets, real RTSP URLs, local DB files, generated
  reports, generated results, videos, model weights, caches, `dist`, or
  `node_modules`.
- `backend/smarttraffic.db`, `.sqlite`, `.sqlite3`, `.db`, `__pycache__`,
  `*.pyc`, `.pytest_cache`, and `/tmp/smarttraffic-vite-build` must remain
  untracked or removed after validation.
- Safety checks must include danger check and a tracked forbidden-file scan
  before commit.

## 6. Required Validation Commands

```bash
git diff --check
./backend/.venv/bin/python -m pytest backend/tests -q
python3 -m py_compile scripts/seed_demo_data.py
cd frontend && npm run build
docker compose config
docker compose build
./backend/.venv/bin/python -m pytest backend/tests/test_seed_demo_data.py -q
python3 scripts/danger_check.py
git status -sb
git log --oneline -n 5
```

If the Docker daemon or external image registry is unavailable, record that
`docker compose build` was not completed for environment reasons. Do not report
a fake Docker build pass.

## 7. Remaining Boundaries

- SmartTraffic is not a formal traffic enforcement system.
- SmartTraffic is not production-ready.
- SmartTraffic is not law-enforcement-grade.
- SmartTraffic is not commercial deployment.
- SmartTraffic is not production IAM.
- Realtime preview is not production realtime monitoring.
- Detection mAP is VOC-style single-IoU, not COCO official.
- IDF1 / MOTA are lightweight deterministic metrics, not TrackEval official.
- Demo validation is not a real-world traffic benchmark.
- Regression is deterministic replay / stored rule replay, not full video
  pipeline rerun.
- SQLite and Docker Compose are for local prototype reproducibility.
