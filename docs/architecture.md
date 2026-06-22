# Architecture

SmartTraffic follows the manual's layered boundary:

```text
React frontend
  -> FastAPI API layer
  -> services
  -> cv / trajectory / events / analysis packages
  -> local storage and future database
```

Phase one implements only the runnable skeleton:

- `backend/app/api`: HTTP routes.
- `backend/app/services`: orchestration and in-memory phase-one registries.
- `backend/app/cv`: YOLOv8 detector adapter, frame reader, video writer, DeepSORT placeholder.
- `backend/app/analysis`: Traffic Analysis Center run directory and metadata writer.
- `frontend/src`: Vite/React page and component skeletons.

Future phases should keep YOLOv8, DeepSORT, Trajectory Engine, Event Engine, Review Center, Bad Case Center, and Evaluation Center separate.
