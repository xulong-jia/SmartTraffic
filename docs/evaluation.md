# Evaluation Center 规划说明

本文档是 Evaluation Center 的 planned design placeholder，不是已实现文档。
当前 SmartTraffic 仍停留在 Stage 7 artifact-backed MVP 边界内，没有实现
Evaluation Center、Bad Case Center、评测数据集、指标计算或回归评测。

## 1. 当前状态

Evaluation Center 尚未实现。当前代码中的 `backend/app/api/evaluation.py`、
`backend/app/services/evaluation_service.py` 和 `scripts/run_evals.py` 只保留
Stage 8 planned placeholder。

当前未实现：

- `evaluation_datasets`
- `evaluation_results`
- detection metrics：mAP、Precision、Recall
- tracking metrics：IDF1、MOTA、ID Switch
- trajectory metrics
- event metrics
- flow counting metrics
- Bad Case regression
- `evaluation_summary.json` 真实生成

## 2. 已有基础

Stage 1-7 已提供 Evaluation Center 后续可读取的 artifact 基础：

- detection artifacts：`detections.csv`、`detections.jsonl`
- tracking artifacts：`tracks.csv`、`tracks.jsonl`
- trajectory artifacts：`trajectory_points.csv`、`trajectory_points.jsonl`
- event artifacts：`events.jsonl`、`event_evidence.jsonl`、`rule_executions.jsonl`
- alert artifacts：`alerts.jsonl`
- traffic statistics artifacts：`flow_counts.json`、`zone_statistics.json`
- visual artifacts：`keyframes/index.json`、keyframe images、`annotated_video.mp4`
- review artifacts：`review_comments.jsonl`、`event_review_state.json`、`false_negative_events.jsonl`
- run management artifacts：`metadata.json`、`manifest.json`、`artifact_index.json`

这些产物能作为 Stage 8 设计输入，但不等同于评测结果或 ground truth。

## 3. Stage 8 目标

Stage 8 计划建立错误样例与评测回归体系：

- 设计 Evaluation Center 的数据模型、artifact contract 和 API contract。
- 管理评测数据集和预期输出。
- 对 detection、tracking、trajectory、event、flow counting 计算指标。
- 将失败样例与 Bad Case Center 建立清晰边界和关联。
- 生成可复查的 evaluation artifacts 和报告。

## 4. 非目标

当前文档不代表以下能力已完成：

- 不实现真实 Evaluation API。
- 不实现 metrics、datasets、reports 或 regression workflow。
- 不实现 Bad Case Center。
- 不做数据库 migration。
- 不做 DB-backed result index。
- 不做权限系统、实时流或生产部署。

## 5. Planned artifacts

Stage 8 后续可考虑的 planned artifacts：

- `evaluation_summary.json`
- `evaluation_metrics.json`
- `evaluation_failures.jsonl`
- `evaluation_dataset_manifest.json`
- `bad_case_regression_results.json`

这些文件目前只属于规划，不应被当前 Stage 7 MVP 当作已生成产物。

## 6. Planned API

Stage 8 后续可考虑的 planned API：

- `POST /api/evaluation/run`
- `GET /api/evaluation/results`
- `GET /api/evaluation/results/{evaluation_id}`
- `GET /api/evaluation/datasets`
- `POST /api/evaluation/datasets`
- `GET /api/evaluation/results/{evaluation_id}/failures`

当前只有 `GET /api/evaluation/results` placeholder，用于保留模块边界。

## 7. Planned metrics

Stage 8 后续可考虑的指标：

- Detection：mAP、Precision、Recall
- Tracking：IDF1、MOTA、ID Switch、track lost count
- Trajectory：track length、lost track、speed/direction consistency
- Event：Event Accuracy、False Alarm Rate、Event Recall、Event F1
- Flow counting：MAE、MAPE
- Bad Case regression：regression pass rate

指标定义必须在 Stage 8A 先明确数据集、ground truth、匹配规则、时间窗口和排除项。

## 8. 与 Bad Case Center 的关系

Evaluation Center 负责评测运行、指标和失败样例归档。Bad Case Center 负责
错误案例生命周期、根因、标签、修复状态和回归状态。

Stage 7 的 false-positive / false-negative review artifacts 不是完整 Bad Case
记录，也不是 Evaluation Center 的 ground truth。Stage 8 需要明确从 review
records 到 bad cases、再到 evaluation regression 的转换规则。

## 9. 与当前 Stage 1-7 的边界

Stage 1-7 当前已完成 artifact-backed MVP：

- 可以按 `run_id` 查询检测、跟踪、轨迹、事件、告警和统计 artifact。
- 可以在 Review Center 复核事件、备注和补充 false-negative record。
- 可以生成 visual artifacts 供人工复核。

但当前仍不是 database-backed final version，也没有实现 Evaluation Center。
`evaluation_summary.json` 在 artifact contract 中是 later-stage reserved key。

## 10. Stage 8A 建议

如果继续推进 Stage 8，建议先做 Stage 8A 只读设计，而不是直接开发：

- 审计现有 artifacts 与 Review Center 数据能否支撑评测。
- 定义 Evaluation 与 Bad Case 的边界。
- 设计 datasets、results、metrics、failures 和 regression contract。
- 明确哪些能力继续 artifact-backed，哪些需要数据库 migration。
- 先更新设计文档和 API contract，再进入实现。
