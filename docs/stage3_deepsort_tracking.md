# Stage 3 DeepSORT Tracking

## Goal

Stage three adds a tracking layer after stage-two YOLOv8 detection. The pipeline now runs video frames through detection, passes frame detections into `DeepSortTracker`, assigns stable `track_id` values, and writes tracking artifacts for each `run_id`.

This stage does not calculate trajectory features, traffic events, alerts, review decisions, bad cases, or evaluation metrics.

## Module Structure

- `backend/app/cv/deepsort_tracker.py`: DeepSORT adapter plus deterministic dry-run tracker fallback.
- `backend/app/services/tracking_service.py`: detection -> tracking orchestration.
- `backend/app/analysis/artifact_writer.py`: detection and tracking artifact writers.
- `backend/app/cv/video_writer.py`: detection and track overlay helpers.
- `backend/app/api/videos.py`: `mode=detection_tracking` process API.
- `backend/app/api/analysis_runs.py`: detection and tracks query API.
- `frontend/src/pages/VideoCenterPage.tsx`: upload and start tracking.
- `frontend/src/pages/AnalysisDetailPage.tsx`: detection and tracking summaries.

## Tracking Contract

Input detections come from the stage-two contract:

```json
{
  "frame_index": 128,
  "timestamp_ms": 4266,
  "detections": [
    {
      "class_name": "car",
      "class_id": 2,
      "confidence": 0.91,
      "bbox": [420.0, 180.0, 520.0, 260.0]
    }
  ]
}
```

Tracking output uses this stable contract:

```json
{
  "frame_index": 128,
  "timestamp_ms": 4266,
  "tracks": [
    {
      "track_id": 17,
      "class_name": "car",
      "class_id": 2,
      "confidence": 0.88,
      "bbox": [420.0, 180.0, 520.0, 260.0],
      "center": [470.0, 220.0],
      "state": "confirmed"
    }
  ]
}
```

## API Usage

Run stage-three detection + tracking in dry-run mode:

```bash
curl -X POST http://localhost:8000/api/videos/{video_id}/process \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "detection_tracking",
    "detector_dry_run": true,
    "tracker_dry_run": true,
    "frame_stride": 1,
    "max_frames": 120
  }'
```

Query outputs:

```bash
curl http://localhost:8000/api/analysis-runs/{run_id}
curl http://localhost:8000/api/analysis-runs/{run_id}/detections?limit=100
curl http://localhost:8000/api/analysis-runs/{run_id}/tracks?limit=100
```

`POST /api/videos/{video_id}/process` also supports `mode=detection_only` for the stage-two path.

## Artifact Directory

```text
results/traffic_analysis/<run_id>/
  metadata.json
  detections.csv
  detections.jsonl
  detection_summary.json
  tracks.csv
  tracks.jsonl
  tracking_summary.json
  tracking_preview.mp4
  keyframes/
```

`tracking_preview.mp4` is only written when requested with `write_preview=true`.

## Dry-Run Tracker vs Real DeepSORT

Dry-run tracker:

- Does not require DeepSORT weights, GPU, network, or ReID embeddings.
- Uses deterministic IoU / center-distance matching.
- Keeps nearby detections on adjacent frames assigned to the same `track_id`.
- Supports basic `confirmed`, `tentative`, and `lost` states for the artifact contract.
- Is used by automated tests.

Real DeepSORT mode:

- Set `DEEPSORT_DRY_RUN=false`.
- If `deep-sort-realtime` is available in the environment, `DeepSortTracker` uses it.
- If the optional dependency is unavailable, SmartTraffic falls back to the deterministic dry-run tracker and records the fallback reason in tracker info.
- YOLOv8 remains responsible only for detections. DeepSORT is responsible only for `track_id` assignment.

## Acceptance

Stage-three acceptance commands:

```bash
cd backend
pytest -q
python -m compileall app

cd ../frontend
npm install
npm run build
```

The tests use temporary videos, dry-run detection, and dry-run tracking. They do not require real YOLOv8 weights, real DeepSORT weights, GPU, network, large videos, `node_modules`, or frontend build artifacts.
