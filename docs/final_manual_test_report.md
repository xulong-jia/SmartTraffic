# SmartTraffic Final Manual Test Report

## 1. Test Environment

| Item | Value |
| --- | --- |
| OS | macOS |
| Runtime | Docker Compose local environment |
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| YOLO model | Local `local_models/yolov8n.pt` |
| Detector mode | Real YOLO detector (`YOLO_DRY_RUN=false`) |
| Tracker mode | Local dry-run tracker for stable validation (`DEEPSORT_DRY_RUN=true`) |

## 2. Test Videos

Local test videos:

- `traffic_jam.mp4`
- `road_flow.mp4`
- `parking_lot.mp4`
- `pedestrian_crossing.mp4`
- `wrong_way_test.mp4`

These files are local runtime assets and are not committed to the repository.

## 3. Main Workflow Test Results

| Step | Operation | Result | Status |
| --- | --- | --- | --- |
| 1 | Start system | Frontend and backend opened through local Docker Compose / one-click launch workflow. | Passed |
| 2 | Upload video | Local MP4 test video uploaded through Video Center. | Passed |
| 3 | Create analysis run | Analysis run created for the uploaded video. | Passed |
| 4 | Run detection / tracking / trajectory | Real YOLO detection completed; tracking and trajectory outputs were generated. | Passed |
| 5 | Create zone | Zone was created in Zone & Rules. | Passed |
| 6 | Create event rule | Event rule was created for `danger_zone_intrusion`. | Passed |
| 7 | Trigger danger zone intrusion | `run_50007c86fd60` produced 14 `danger_zone_intrusion` events. | Passed |
| 8 | View alerts | Alert Center showed 14 generated alerts. | Passed |
| 9 | Review confirm | Review Center confirmed the tested event workflow. | Passed |
| 10 | Create bad case | Bad Case Center recorded 1 Bad Case. | Passed |
| 11 | Run evaluation | Evaluation Center generated 5 event metrics; without expected labels, metrics showed `not_applicable` as expected. | Passed |
| 12 | Export report | Report Center exported PDF / JSON / CSV and displayed bundle metadata. | Passed |

## 4. Known Boundaries

- `flow_counting` was not triggered by the current manually verified test video;
  this does not indicate module failure.
- Event metrics without expected labels returning `not_applicable` is expected
  behavior.
- SmartTraffic is a local validation / portfolio demo, not a production traffic
  enforcement system.

## 5. Final Conclusion

The main local showcase chain passed: upload video, process analysis, configure
zone and event rule, trigger event, generate alerts, confirm review, create Bad
Case, run evaluation, and export reports.
