# Stage 2 YOLOv8 Detection

## Goal

Stage two connects SmartTraffic's video upload and processing skeleton to a YOLOv8 detection pipeline. It stops at detection output generation and does not enter tracking, trajectory analysis, event rules, alerts, review, bad cases, or evaluation.

## Module Structure

- `backend/app/cv/yolo_detector.py`: detector adapter, dry-run mode, optional `ultralytics.YOLO` inference, detection normalization.
- `backend/app/cv/frame_reader.py`: video metadata and frame iteration.
- `backend/app/cv/video_writer.py`: detection drawing and optional preview writer.
- `backend/app/services/detection_service.py`: stage-two detection orchestration.
- `backend/app/analysis/artifact_writer.py`: run directory and artifact writing.
- `backend/app/api/videos.py`: upload and process API.
- `backend/app/api/analysis_runs.py`: run metadata and detection artifact query API.

## Detection Contract

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

Default target classes are `car`, `bus`, `truck`, `motorcycle`, `bicycle`, and `person`.

## API Usage

Upload a video:

```bash
curl -F "file=@sample.mp4" http://localhost:8000/api/videos/upload
```

Run stage-two detection in dry-run mode:

```bash
curl -X POST http://localhost:8000/api/videos/{video_id}/process \
  -H "Content-Type: application/json" \
  -d '{"mode": "detection_only", "dry_run": true, "frame_stride": 1, "max_frames": 120}'
```

Query a run:

```bash
curl http://localhost:8000/api/analysis-runs/{run_id}
curl http://localhost:8000/api/analysis-runs/{run_id}/detections?limit=100
```

## Artifact Directory

```text
results/traffic_analysis/<run_id>/
  metadata.json
  detections.csv
  detections.jsonl
  detection_summary.json
  detection_preview.mp4
  keyframes/
```

`detection_preview.mp4` is only written when requested with `write_preview=true`.

## Dry-Run vs Real Inference

Dry-run mode:

- Does not import `ultralytics` or `torch`.
- Does not require model weights.
- Returns stable empty detections by default.
- Is used by automated tests.

Real inference mode:

- Set `YOLO_DRY_RUN=false`.
- Set `YOLO_MODEL_PATH` to a local, untracked model file such as `local_models/best.pt`.
- Requires `ultralytics` and `torch` to be installed.
- Converts YOLOv8 output into the SmartTraffic detection contract.

## Acceptance

Stage-two acceptance commands:

```bash
cd backend
pytest -q

cd ../frontend
npm install
npm run build
```

The tests use temporary videos and dry-run detection only. They do not require real weights, GPU, network, large videos, or external services.
