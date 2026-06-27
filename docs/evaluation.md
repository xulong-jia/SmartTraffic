# Evaluation Center

本文档记录 Stage 8HI 后的 Evaluation Center artifact-backed MVP、Full
Stage 3EF 后的 Evaluation DB workflow，以及 Full Stage 5E 的 Evaluation
前端展示增强。它仍不代表工业级检测 / 跟踪评测体系已经完成。

## 当前状态

Stage 8EFG / Stage 8HI 已实现：

- `evals/datasets/evaluation_datasets.json` 数据集注册表。
- `evals/results/evaluation_runs.jsonl` 评测运行记录。
- `evals/results/evaluation_results.jsonl` 指标结果记录。
- `evals/results/failed_cases.jsonl` Evaluation failed cases。
- `results/traffic_analysis/{run_id}/evaluation_summary.json` run-level summary。
- Evaluation API、CLI 和 Evaluation Center 前端 MVP。
- `POST /api/bad-cases/from-failed-case` failed case -> Bad Case MVP。
- Bad Case regression summary MVP。

Full Stage 3EF 已实现：

- `evaluation_datasets` DB-backed dataset registry。
- `evaluation_results` DB-backed result persistence。
- failed cases 持久化在 `evaluation_results.summary["failed_cases"]` 中；没有新增
  failed_cases 独立表。
- Evaluation API DB-first 查询，DB 缺失时 fallback 到 artifacts。
- `scripts/run_evals.py --write-db --database-url ...` 可选写入 DB，同时保留
  artifact 输出。
- failed cases 可通过 `POST /api/bad-cases/from-failed-case` 转为 DB Bad Case，
  同一 `run_id + failed_case_id` 幂等。

Full Stage 4AB 已实现：

- Trajectory final features：`zone_history`、`lane_relation`、`line_crossings`、
  `dwell_time_ms`、像素速度、`moving_angle` 和 `direction_consistency`。
- 六类 Event Rule final behavior：wrong-way、illegal parking、danger zone、
  pedestrian lane、congestion 和 flow counting 使用稳定 trajectory features。
- 这些 features 可被后续 evaluation 使用。

Full Stage 4CD 已实现：

- Detection benchmark algorithm foundation：IoU、按 class 和单一 IoU threshold
  贪心匹配、precision、recall、per-class AP 和 mAP。
- Tracking benchmark algorithm foundation：逐帧 IoU association、IDF1、MOTA、
  ID switch 和 track lost segment 统计。
- `evaluation_type=detection` / `tracking` 已接入 EvaluationService；
  有 tiny fixture annotations 时可把 mAP / precision / recall / per-class AP
  以及 IDF1 / MOTA / ID switch / track lost 写入 `evaluation_results`。
- Tracking evaluation 会把 ID switch 和 track lost segment 输出为 Evaluation
  failed cases，`suggested_bad_case_type` 分别为 `id_switch` 和 `track_lost`，
  供显式 Bad Case 转换使用。
- 没有 annotation 时返回 `status=insufficient_data`、
  `reason=not_enough_annotations`，不写假指标。

Full Stage 4E 已实现：

- Bad Case regression evaluation 不再只是 status summary。
- 支持 status-based deterministic replay：读取 Bad Case 的
  `regression_replay.actual_result` / `passed`，与 expected result 比较。
- 支持 rule replay fixture：读取 Bad Case payload 中的 `rule_replay.rules`、
  `trajectory_frames` 和 expected event count，调用 EventEngine 做确定性回放。
- 输出 per-case regression results、`regression_pass_rate`、
  `fixed_case_count`、`reopened_case_count`、`failed_case_count`、
  `by_case_type` 和 `by_module`。
- `apply_updates` 默认 `false`，只返回 fixed / reopened 建议；显式设置
  `apply_updates=true` 时，open / triaged 且 replay passed 的 case 会更新为
  `fixed`，fixed / verified 且 replay failed 的 case 会重新打开为 `open`。
- failed regression cases 会作为 Evaluation failed cases 写入 artifacts 和
  DB-backed `evaluation_results.summary["failed_cases"]`。

Full Stage 5E 已实现：

- Evaluation Center 提供 run / dataset / evaluation type 选择和过滤。
- Results 区展示 metric cards、结果列表和 JSON-friendly detail payload。
- Failed Cases 区展示 failed-case 表，并可调用
  `POST /api/bad-cases/from-failed-case` 创建 Bad Case。
- Summary 区展示 Bad Case regression summary cards 和完整 summary JSON。
- UI 明确标注边界：detection mAP 是 VOC-style single-IoU，不是 COCO
  official；tracking IDF1 / MOTA 是 lightweight deterministic，不是 TrackEval
  official；regression 是 deterministic replay / stored rule replay，不是完整视频
  rerun；`insufficient_data` 表示缺少 annotations / replay data，不是零分或失败。

当前仍未实现：

- 完整视频级 YOLO / DeepSORT / Trajectory pipeline rerun。
- COCO official multi-threshold mAP。
- TrackEval official tracking metrics。
- 权限、多用户、实时流或生产部署。

## Artifacts

Evaluation artifacts 位于 `evals/`，真实 generated results 不应提交到 Git。
仓库可以保留 `.gitkeep` 和 Stage 9CD 小型 toy expected files；`evals/results/`
仍只保留 `.gitkeep`，真实 evaluation run/result/failed-case artifacts 不提交。

```text
evals/
  datasets/
    evaluation_datasets.json
  expected/
  results/
    evaluation_runs.jsonl
    evaluation_results.jsonl
    failed_cases.jsonl
```

每次评测还会在对应 analysis run 目录写入：

```text
results/traffic_analysis/{run_id}/evaluation_summary.json
```

该文件会同步刷新 `metadata.json`、`manifest.json` 和 `artifact_index.json`
中的 `evaluation_summary` 状态，但不会覆盖 detection、tracking、trajectory、
event、alert、review 或 Bad Case 原始 artifacts。

## Demo Validation Samples

`scripts/seed_demo_data.py` writes tiny local sample configs and expected files
for validation smoke tests. `evals/expected/demo_expected_events.json` covers
the six supported event types with synthetic expected events:

- `wrong_way_driving`
- `danger_zone_intrusion`
- `flow_counting`
- `illegal_parking`
- `pedestrian_in_vehicle_lane`
- `congestion`

These files are toy local validation inputs. They are not a real traffic video
benchmark and do not claim production detection, tracking, or road-level
generalization.

## API

Stage 8EFG 提供以下 endpoints；Full Stage 3EF 后这些接口对 DB run 使用
DB-first 行为，并保留 artifact fallback：

- `GET /api/evaluation/datasets`
- `POST /api/evaluation/datasets`
- `GET /api/evaluation/runs`
- `POST /api/evaluation/run`
- `GET /api/evaluation/results`
- `GET /api/evaluation/summary/{run_id}`
- `GET /api/evaluation/failed-cases`

Bad Case / Evaluation 联动 endpoint：

- `POST /api/bad-cases/from-failed-case`

`POST /api/evaluation/run` 支持 `event`、`flow_counting`、`trajectory`、
`detection`、`tracking`、`regression` 类型。其中 `regression` 读取 DB
bad cases 或当前 run 的 `bad_cases.jsonl`，执行 deterministic replay /
rule replay regression；它不执行完整视频模型重跑。

## Metrics MVP

当前指标是 artifact-backed MVP：

- Event：按 `event_type` 和 frame range overlap / tolerance 做贪心匹配，
  输出 `event_accuracy`、`event_precision`、`event_recall`、`event_f1` 和
  `false_alarm_rate`，并把 unmatched expected / actual 写为 failed cases。
  当前 local definition 为：
  - `event_accuracy = TP / expected_events`，表示 expected events 中被匹配的比例；没有 TN 口径，不代表真实道路总体准确率。
  - `event_recall = TP / (TP + FN)`。
  - `false_alarm_rate = FP / predicted_events`，等价于 `FP / (TP + FP)`；没有预测时为 0。
  - `event_f1 = 2 * precision * recall / (precision + recall)`。
  Details payload 还包含 per-event-type metrics；这些指标只用于 synthetic /
  sample / local validation，不是官方 benchmark。
- Flow counting：比较 expected counts 与 `flow_counts.json` 的 total、
  class、direction 误差，输出 absolute error、MAE、MAPE。
- Trajectory：从 `trajectory_points.jsonl` 统计 track count、trajectory
  point count、average track length、average speed、direction availability。
- Detection：读取 detection annotations 与 `detections.jsonl`，输出
  `detection_mAP`、`detection_precision`、`detection_recall` 和
  `detection_ap_<class>`。当前 mAP 是 VOC-style single-IoU AP，默认 IoU
  threshold 为 0.5；它不是 COCO official mAP。
- Tracking：读取 tracking annotations 与 `tracks.jsonl`，输出 `tracking_idf1`、
  `tracking_mota`、`tracking_id_switches` 和 `tracking_track_lost`。当前实现是
  lightweight deterministic frame-level association；它不是 TrackEval official
  implementation。`id_switch` 和 `track_lost` 会作为 Evaluation failed cases
  输出，可通过 failed-case -> Bad Case 流程显式转换。
- Detection / Tracking：若没有 annotation，返回 `insufficient_data` /
  `not_enough_annotations`；不伪造真实 benchmark dataset 指标。
- Regression：读取 Bad Case replay payload，输出 per-case replay result、
  `total_case_count`、`evaluated_case_count`、`passed_case_count`、
  `failed_case_count`、`fixed_case_count`、`reopened_case_count`、
  `ignored_case_count`、`insufficient_data_count` 和 `regression_pass_rate`。
  没有 replay payload 时返回 `insufficient_data`，不伪造 pass。

Bad Case regression 口径：

```text
regression_pass_rate = passed_case_count / max(passed_case_count + failed_case_count, 1)
```

该指标来自 deterministic replay / rule replay。`apply_updates=false` 为默认
策略，不修改 Bad Case；`apply_updates=true` 才会按 replay 结果更新 fixed 或
reopened 状态。该阶段不是完整视频 pipeline rerun。

## CLI

```bash
python3 scripts/run_evals.py \
  --run-id run_xxx \
  --dataset-id dataset_xxx \
  --evaluation-type event \
  --json
```

可选参数：

- `--results-root`
- `--eval-root`
- `--evaluation-type event|flow_counting|trajectory|detection|tracking|regression`
- `--write-db`
- `--no-write-db`
- `--database-url sqlite:///...`
- regression filters：`--case-type`、`--module`、`--status`、`--tag`
- regression update switch：`--apply-updates`

## 与 Bad Case / Review 的边界

Evaluation failed cases 是评测失败记录，不等于 Bad Case Center 的
`bad_cases.jsonl` 或 `bad_cases` DB rows。Stage 8HI 提供显式转换 MVP；Full
Stage 3EF 后，调用 `POST /api/bad-cases/from-failed-case` 会优先查 DB
`evaluation_results.summary["failed_cases"]`，创建 `source=evaluation_center`、
`linked_failed_case_id=<failed_case_id>` 的 DB Bad Case；DB 缺失时 fallback 到
`evals/results/failed_cases.jsonl` 和 artifact-backed Bad Case 行为。该操作不会
修改 failed case 原始记录。

Review Center 的 `false_positive` / `false_negative` 是人工复核状态，也不是
Evaluation ground truth。Evaluation 可以读取 Stage 6/7 artifacts，但不修改
Review artifacts。
