# Stage 8 Bad Case 与 Evaluation Center 设计文档

本文档是 Stage 8A 的只读审计与设计文档。当前仓库仍停留在 Stage 7 artifact-backed MVP 之后，尚未实现 Bad Case Center、Evaluation Center、数据库迁移、真实评测指标、回归评测或生产化评测平台。

本文档只定义 Stage 8 后续开发边界、artifact contract、API contract、前端页面草案、测试策略和子阶段拆分，不代表任何 Stage 8 功能已经实现。

## 1. 阶段目标

Stage 8 的目标是在不破坏 Stage 1-7 artifact-backed MVP 的前提下，补齐 SmartTraffic 的错误样例资产和评测回归闭环。

Stage 8 应完成两个中心：

- Bad Case Center：把误报、漏报、ID Switch、Track Lost、规则错误和区域配置错误沉淀为可归因、可查询、可统计、可回归的错误样例资产。
- Evaluation Center：基于已有 run artifacts、评测数据集和预期输出，生成检测、跟踪、轨迹、事件、流量统计和 Bad Case regression 的 artifact-backed MVP 评测结果。

Stage 8 的最小工程口径仍建议采用 artifact-backed MVP。数据库最终版可以在后续明确迁移阶段再做。

## 2. 非目标

Stage 8 暂不做：

- 不做真实数据库 migration。
- 不做 DB-backed result index。
- 不做生产级评测平台。
- 不做大规模公开数据集下载器。
- 不做模型训练。
- 不做真实世界交通标定。
- 不做执法级判断。
- 不做多用户权限。
- 不做实时流生产部署。
- 不做复杂 ML experiment tracking。
- 不做完整工业级 mAP / IDF1 / MOTA 实现；如果当前没有标注数据，先做 artifact-backed MVP 和可扩展接口。

## 3. 当前基础审计

### 3.1 已有能力

当前 Stage 1-7 已经提供以下基础：

- `GET /api/analysis-runs/{run_id}`、manifest、detections、tracks、trajectory-points、events、alerts、flow-counts、zone-statistics 等 artifact-backed 读取入口。
- Stage 6 run artifacts：`metadata.json`、`manifest.json`、`artifact_index.json`、`detections.csv/jsonl`、`tracks.csv/jsonl`、`trajectory_points.csv/jsonl`、`events.jsonl`、`event_evidence.jsonl`、`rule_executions.jsonl`、`alerts.jsonl`、`flow_counts.json`、`zone_statistics.json`、`keyframes/index.json`、`annotated_video.mp4`。
- Stage 7 review artifacts：`review_comments.jsonl`、`event_review_state.json`、`false_negative_events.jsonl`。
- Review API 已支持事件列表、事件详情、confirm、false-positive、ignore、resolve、comments 和 false-negative creation。
- Review Center 前端已能读取 `/api/review`，展示 review status、comments、linked alerts、visual artifacts，并能补充 false-negative record。
- Analysis Detail 和 Alert Center 已能跳转到 Review Center。
- `evals/` 目录已存在 `datasets/`、`expected/`、`results/`、`scripts/` 基础目录，并只提交 `.gitkeep`。
- `.gitignore` 已排除真实 results、local videos、local models、模型权重、视频、cache、dist、node_modules。

### 3.2 部分能力

当前已有但尚未形成 Stage 8 完整能力的部分：

- `docs/evaluation.md` 是 planned placeholder，列出 Evaluation Center 目标和边界，但不包含完整 Stage 8 实施拆分。
- `scripts/run_evals.py` 是 Stage 8 planned evaluation runner placeholder，不运行真实评测。
- `scripts/seed_demo_data.py` 是 Stage 9 planned demo seed placeholder，不生成真实 demo/eval 数据。
- `backend/app/analysis/artifact_writer.py` 已将 `evaluation_summary.json` 作为 later-stage reserved artifact key，但没有真实生成逻辑。
- `backend/app/schemas/review.py` 已定义 review status/action 与 false-negative schema，可作为 Bad Case 来源之一。
- `frontend/src/App.tsx` 已暴露 `Bad Case Center (planned)` 和 `Evaluation Center (planned)` 导航入口。

### 3.3 未实现能力

当前未实现：

- `/api/bad-cases` 真实查询、创建、更新、summary。
- `/api/evaluation/results` 真实查询。
- Bad Case artifact helper、schema、service、API、前端。
- Evaluation dataset config、evaluation run registry、metrics、results、summary、failed cases。
- `evaluation_summary.json` 真实生成。
- failed case 转 Bad Case。
- Review false-positive / false-negative 自动派生 Bad Case。
- Bad Case regression。
- 数据库模型、repository、migration。

### 3.4 当前风险

Stage 8 开发前需要控制以下风险：

- 把 Stage 7 的 `false_positive` / `false_negative` review state 误认为完整 Bad Case。
- 把 `review_comments.jsonl` 误认为 Evaluation report。
- 把 Stage 6 的 `flow_counts.json` / `zone_statistics.json` 误认为评测指标。
- 在没有 ground truth 的情况下宣称 mAP、IDF1、MOTA、Event F1 等工业级指标已完成。
- 直接覆盖 Stage 5/6 原始 artifacts，破坏复查链路。
- 过早引入数据库和复杂评测平台，扩大 Stage 8 MVP 范围。
- 提交 generated evaluation results、视频、模型权重或大文件。

## 4. Stage 8 总体设计

### 4.1 Bad Case Center 的职责

Bad Case Center 负责管理错误样例资产。它不直接重新计算检测、跟踪、轨迹或事件规则，而是引用已有 run artifacts、Review artifacts 和 Evaluation failed cases。

职责包括：

- 创建 Bad Case。
- 查询 Bad Case。
- 更新状态、root cause、tags 和备注字段。
- 关联 `run_id`、`video_id`、`event_id`、`track_id`、`frame_index`、`snapshot_path`。
- 支持 `false_positive`、`false_negative`、`id_switch`、`track_lost`、`rule_error`、`zone_config_error`。
- 支持 `detector`、`tracker`、`trajectory`、`event_engine`、`zone_config`、`review`、`evaluation` 模块归因。
- 从 Review Center 的 false-positive / false-negative 派生或关联 Bad Case。
- 从 Evaluation failed case 派生 Bad Case。
- 提供按 `case_type`、`module`、`status`、`tags` 的统计。

### 4.2 Evaluation Center 的职责

Evaluation Center 负责管理评测数据、执行 artifact-backed MVP 评测、保存评测结果和失败样例。

职责包括：

- 管理 `evaluation_datasets.json`。
- 记录 `evaluation_runs.jsonl`。
- 写入 `evaluation_results.jsonl`。
- 生成 `evaluation_summary.json`。
- 写入 `failed_cases.jsonl`。
- 提供检测、跟踪、轨迹、事件、流量统计和 Bad Case regression 的可扩展指标接口。
- 在 MVP 中先对已有 artifacts 与 expected artifacts 做确定性比较，不宣称工业级完整评测。

### 4.3 与 Stage 6 Traffic Analysis Center 的边界

Stage 6 Traffic Analysis Center 负责按 `run_id` 组织和读取分析结果，不负责评测业务。

边界如下：

- Stage 6 的 `flow_counts.json` / `zone_statistics.json` 是统计产物。
- Stage 8 的 flow evaluation 是对统计产物与 expected counts 的误差评测。
- Stage 6 的 `evaluation_summary.json` 目前只是 planned artifact key。
- Stage 8 才真正生成 `evaluation_summary.json`。
- Stage 8 可以读取 Stage 6 artifacts，但不应覆盖原始 `detections`、`tracks`、`trajectory_points`、`events`、`alerts`、`flow_counts` 或 `zone_statistics`。

### 4.4 与 Stage 7 Review Center 的边界

Stage 7 Review Center 负责人工复核事件状态、备注和补充漏报。Stage 8 Bad Case / Evaluation 负责错误资产和评测回归。

边界如下：

- Stage 7 的 `false_positive` / `false_negative` 是 Review 状态和人工补充记录。
- Stage 8 的 Bad Case 是可归因、可统计、可回归的错误样例资产。
- `false_negative_events.jsonl` 不等于 Bad Case Center。
- `review_comments.jsonl` 不等于 Evaluation report。
- Bad Case 可以引用 Review artifacts，但不能覆盖 Review artifacts。
- Evaluation 可以读取 Bad Case，但不应修改原始 review records。
- Review Center 可以提供“创建/关联 Bad Case”入口，但 Bad Case 生命周期应由 Bad Case Center 管理。

### 4.5 Artifact-based MVP 与 DB final 的边界

Stage 8 MVP 建议继续使用本地 artifacts：

- 快速继承 Stage 6/7 的 run directory 边界。
- 避免过早引入数据库 migration。
- 保持本地可验证、可测试、可提交的小步交付。

DB final 后续可将以下 artifacts 迁移为结构化表：

- `bad_cases.jsonl` -> `bad_cases`
- `evaluation_datasets.json` -> `evaluation_datasets`
- `evaluation_runs.jsonl` -> `evaluation_runs`
- `evaluation_results.jsonl` -> `evaluation_results`
- `failed_cases.jsonl` -> `evaluation_failed_cases`

但 Stage 8 artifact-backed API contract 应尽量保持与 DB final response 语义兼容。

## 5. Bad Case 数据设计

### 5.1 bad_cases.jsonl

Stage 8B 建议在 run directory 中新增：

```text
results/traffic_analysis/{run_id}/bad_cases.jsonl
```

也可在后续 Stage 8H 增加跨 run 索引：

```text
results/traffic_analysis/bad_case_index.json
```

`bad_cases.jsonl` 单条结构建议：

```json
{
  "case_id": "bc_xxx",
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "event_id": "event_xxx",
  "track_id": 17,
  "frame_index": 120,
  "case_type": "false_positive",
  "module": "event_engine",
  "description": "System reported wrong-way event but reviewer marked it false positive.",
  "expected_result": "no event",
  "actual_result": "wrong_way_driving",
  "root_cause": "direction threshold too sensitive",
  "snapshot_path": "keyframes/event_xxx_120.jpg",
  "tags": ["wrong_direction"],
  "status": "open",
  "source": "review_center",
  "linked_review_id": "review_xxx",
  "linked_failed_case_id": null,
  "created_at": "2026-06-26T00:00:00Z",
  "updated_at": "2026-06-26T00:00:00Z"
}
```

字段规则：

- `case_id` 必填，建议稳定前缀 `bc_`。
- `run_id` 必填。
- `video_id` 推荐必填；如果旧 run metadata 缺失，可从 run summary 派生。
- `event_id`、`track_id`、`frame_index` 允许为空，但至少应有一个定位字段或 `description` 说明。
- `snapshot_path` 必须是 run directory 内相对路径。
- `tags` 必须是字符串数组。
- `created_at` / `updated_at` 使用 UTC ISO 字符串。

### 5.2 Bad Case 类型

Stage 8 MVP 支持以下 `case_type`：

| case_type | 含义 | 常见来源 |
| --- | --- | --- |
| `false_positive` | 系统产生结果，但人工或 expected output 认为不应成立 | Review / Evaluation |
| `false_negative` | 实际存在目标或事件，但系统未产生对应结果 | Review / Evaluation |
| `id_switch` | 同一目标跟踪 ID 发生切换 | Evaluation |
| `track_lost` | 目标轨迹中断或丢失 | Evaluation |
| `rule_error` | 事件规则触发、阈值或状态逻辑错误 | Review / Evaluation |
| `zone_config_error` | 区域、方向线或计数线配置导致错误 | Review / Evaluation |

### 5.3 Bad Case 状态

Stage 8 MVP 支持以下 `status`：

| status | 含义 |
| --- | --- |
| `open` | 已记录，尚未修复 |
| `fixed` | 已有修复或配置调整，待回归验证 |
| `verified` | 回归评测或人工复核确认已修复 |
| `ignored` | 低优先级、非目标场景或不纳入当前修复 |

状态流转建议：

```text
open -> fixed -> verified
open -> ignored
fixed -> open      # 回归失败或复现
ignored -> open    # 重新纳入
```

### 5.4 Bad Case 来源

`source` 建议支持：

- `review_center`
- `evaluation_center`
- `manual`
- `script`

来源字段只表示创建入口，不代表错误归因。归因由 `module` 字段表达。

### 5.5 与 Review artifacts 的关系

Bad Case 可以引用 Review artifacts：

- `linked_review_id` 引用 `review_comments.jsonl.review_id`。
- `event_id` 引用 Stage 6 原始 event 或 Stage 7 synthetic false-negative id。
- `source=review_center` 表示从 Review 动作派生。

Bad Case 不应修改：

- `review_comments.jsonl`
- `event_review_state.json`
- `false_negative_events.jsonl`
- `events.jsonl`

如果从 Review 创建 Bad Case，建议追加 `bad_cases.jsonl`，并在 response 中返回 `case_id`。是否在 Review detail 派生展示 `bad_case_id` 可由读取层 join 完成。

### 5.6 与 Evaluation failed cases 的关系

Evaluation failed case 是评测运行的一次失败记录，Bad Case 是长期跟踪的错误资产。

关系建议：

- `failed_cases.jsonl.failed_case_id` 可被 `bad_cases.jsonl.linked_failed_case_id` 引用。
- 同一个 failed case 可创建一个 Bad Case。
- 多次 evaluation failed case 可关联到同一个 Bad Case，但 MVP 可以先一对一。
- Evaluation 读取 Bad Case 用于 regression，不应修改 Bad Case 原始记录，状态更新应走 Bad Case API。

## 6. Evaluation 数据设计

### 6.1 evaluation_datasets.json

建议路径：

```text
evals/datasets/evaluation_datasets.json
```

结构建议：

```json
{
  "schema_version": "stage8.evaluation_datasets.v1",
  "datasets": [
    {
      "dataset_id": "dataset_demo_001",
      "name": "Demo traffic evaluation set",
      "dataset_type": "artifact_expected_outputs",
      "source": "local_public_or_synthetic",
      "annotation_path": "evals/expected/demo_annotations.json",
      "expected_events_path": "evals/expected/demo_expected_events.jsonl",
      "expected_counts_path": "evals/expected/demo_expected_counts.json",
      "metadata": {
        "description": "Small public or synthetic sample for Stage 8 MVP",
        "license": "public_or_self_created"
      },
      "created_at": "2026-06-26T00:00:00Z"
    }
  ]
}
```

`dataset_type` MVP 可支持：

- `artifact_expected_outputs`
- `review_seeded`
- `manual_json`

### 6.2 evaluation_runs.jsonl

建议路径：

```text
evals/results/evaluation_runs.jsonl
```

单条结构建议：

```json
{
  "evaluation_run_id": "eval_run_xxx",
  "dataset_id": "dataset_demo_001",
  "run_id": "run_xxx",
  "evaluation_type": "event",
  "status": "completed",
  "started_at": "2026-06-26T00:00:00Z",
  "finished_at": "2026-06-26T00:01:00Z",
  "config": {
    "match_window_ms": 1000,
    "iou_threshold": 0.5,
    "class_match_required": true
  }
}
```

`evaluation_type` MVP 可支持：

- `detection`
- `tracking`
- `trajectory`
- `event`
- `flow_counting`
- `bad_case_regression`

### 6.3 evaluation_results.jsonl

建议路径：

```text
evals/results/evaluation_results.jsonl
```

单条结构建议：

```json
{
  "evaluation_result_id": "eval_result_xxx",
  "evaluation_run_id": "eval_run_xxx",
  "run_id": "run_xxx",
  "dataset_id": "dataset_demo_001",
  "evaluation_type": "event",
  "metric_name": "event_recall",
  "metric_value": 0.75,
  "details": {
    "matched_events": 3,
    "expected_events": 4,
    "notes": "MVP exact event_type and time-window match"
  },
  "created_at": "2026-06-26T00:01:00Z"
}
```

### 6.4 evaluation_summary.json

建议同步写入 run directory：

```text
results/traffic_analysis/{run_id}/evaluation_summary.json
```

结构建议：

```json
{
  "schema_version": "stage8.v1",
  "run_id": "run_xxx",
  "generated_at": "2026-06-26T00:01:00Z",
  "summary": {
    "detection": {},
    "tracking": {},
    "trajectory": {},
    "event": {},
    "flow_counting": {},
    "bad_case_regression": {}
  },
  "failed_cases": []
}
```

`evaluation_summary.json` 应由 Stage 8 Evaluation Center 真实生成。Stage 6 中出现的 `evaluation_summary.json` 只是 planned artifact key。

### 6.5 failed_cases.jsonl

建议路径：

```text
evals/results/failed_cases.jsonl
```

单条结构建议：

```json
{
  "failed_case_id": "fail_xxx",
  "evaluation_run_id": "eval_run_xxx",
  "run_id": "run_xxx",
  "failure_type": "false_negative",
  "module": "event_engine",
  "expected": {
    "event_type": "wrong_way_driving",
    "frame_index": 120
  },
  "actual": {
    "event_type": null
  },
  "frame_index": 120,
  "event_id": null,
  "track_id": 17,
  "snapshot_path": "keyframes/event_xxx_120.jpg",
  "suggested_bad_case_type": "false_negative"
}
```

`failed_cases.jsonl` 是一次 evaluation run 的失败输出，不等于 Bad Case。只有用户或 API 明确转换后，才追加 `bad_cases.jsonl`。

## 7. 指标口径设计

### 7.1 Detection metrics

Planned metrics：

- `mAP`
- `precision`
- `recall`

MVP 限制：

- 若没有 bbox ground truth，不能计算真实 mAP。
- Stage 8E 可以先定义 detection result schema 和 expected annotation schema。
- 可先实现简单 exact class count / confidence threshold summary 作为 smoke metric，但不得命名为工业级 mAP。

### 7.2 Tracking metrics

Planned metrics：

- `IDF1`
- `MOTA`
- `id_switch_count`

MVP 限制：

- 若没有 track ground truth，不能计算真实 IDF1 / MOTA。
- Stage 8E 可先支持基于 expected track id sequence 的小样例统计。
- ID Switch / Track Lost 可先从 expected artifacts 或人工标注 failed cases 输入。

### 7.3 Trajectory metrics

Planned metrics：

- `track_length`
- `lost_track_count`
- `speed_consistency`
- `direction_consistency`

MVP 口径：

- `track_length` 可基于 `trajectory_points.jsonl` 聚合。
- `lost_track_count` 需要 expected track continuity 或 rule-based gap threshold。
- `speed_consistency` / `direction_consistency` 需要 expected trajectories 或阈值规则；缺 ground truth 时只能作为 diagnostic summary。

### 7.4 Event metrics

Planned metrics：

- `event_accuracy`
- `false_alarm_rate`
- `event_recall`
- `event_f1`

MVP 口径：

- 以 expected events JSONL 与 `events.jsonl` 做 `event_type + time window + optional zone/track` 匹配。
- unmatched actual events 计为 false positives。
- unmatched expected events 计为 false negatives。
- `event_f1 = 2 * precision * recall / (precision + recall)`，precision/recall 分母为 0 时返回 null 并在 details 中说明。

### 7.5 Flow counting metrics

Planned metrics：

- `MAE`
- `MAPE`
- `direction_wise_error`
- `class_wise_error`

MVP 口径：

- 读取 Stage 6 `flow_counts.json`。
- 读取 `expected_counts_path`。
- 按 `time_window`、`line_id`、`direction`、`class_name` 对齐后计算误差。
- expected count 为 0 时不计算 MAPE，改写入 details warning。

### 7.6 Bad Case regression metrics

Planned metrics：

- `regression_pass_rate`
- `reopened_case_count`
- `fixed_case_count`

MVP 口径：

- 读取 `bad_cases.jsonl` 中 `status=fixed` 或 `status=verified` 的 case。
- 读取最新 evaluation failed cases。
- 若 fixed case 的同类失败再次出现，可建议从 `fixed` 回到 `open`，但状态更新必须走 Bad Case API。
- `regression_pass_rate = passed_fixed_cases / total_fixed_cases`，分母为 0 时返回 null。

### 7.7 当前 MVP 指标限制

Stage 8 MVP 的指标必须显式声明限制：

- 没有 ground truth 时不能宣称真实 mAP、IDF1、MOTA。
- 小样例评测不能代表生产效果。
- 像素级速度和方向一致性不等于真实世界速度标定。
- Event metrics 依赖 expected events 的标注质量。
- Flow metrics 依赖 expected counts 的窗口、方向和类别定义一致性。

## 8. API Contract 草案

所有 API 本节均为设计草案，不代表当前实现。

### 8.1 Bad Case APIs

#### GET /api/bad-cases

用途：查询 Bad Case 列表。

Query：

- `run_id`: optional string
- `case_type`: optional string
- `module`: optional string
- `status`: optional string
- `tag`: optional string
- `limit`: integer, default 100
- `offset`: integer, default 0

Response：

```json
{
  "items": [],
  "total": 0,
  "limit": 100,
  "offset": 0,
  "filters": {
    "run_id": null,
    "case_type": null,
    "module": null,
    "status": null,
    "tag": null
  }
}
```

Stage：8C。

#### GET /api/bad-cases/{case_id}

用途：查询单个 Bad Case 详情。

Response：

```json
{
  "case": {},
  "linked_review": null,
  "linked_failed_case": null,
  "analysis_run": null,
  "visual_artifacts": {}
}
```

Stage：8C。

#### POST /api/bad-cases

用途：手动创建 Bad Case。

Request：

```json
{
  "run_id": "run_xxx",
  "video_id": "video_xxx",
  "event_id": "event_xxx",
  "track_id": 17,
  "frame_index": 120,
  "case_type": "false_positive",
  "module": "event_engine",
  "description": "Wrong-way event is not valid.",
  "expected_result": "no event",
  "actual_result": "wrong_way_driving",
  "root_cause": "direction threshold too sensitive",
  "snapshot_path": "keyframes/event_xxx_120.jpg",
  "tags": ["wrong_direction"],
  "source": "manual"
}
```

Response：

```json
{
  "status": "created",
  "case_id": "bc_xxx",
  "case": {}
}
```

Stage：8C。

#### PATCH /api/bad-cases/{case_id}

用途：更新 Bad Case 状态、root cause、tags 或 description。

Request：

```json
{
  "status": "fixed",
  "root_cause": "threshold fixed",
  "tags": ["wrong_direction", "threshold"],
  "description": "Updated after rule config change."
}
```

Response：

```json
{
  "status": "updated",
  "case_id": "bc_xxx",
  "case": {}
}
```

Stage：8C。

#### GET /api/bad-cases/summary

用途：返回 Bad Case 统计。

Response：

```json
{
  "total": 0,
  "by_case_type": {},
  "by_module": {},
  "by_status": {},
  "top_tags": []
}
```

Stage：8C。

### 8.2 Evaluation APIs

#### GET /api/evaluation/datasets

用途：查询 evaluation datasets。

Response：

```json
{
  "items": [],
  "total": 0
}
```

Stage：8F。

#### POST /api/evaluation/datasets

用途：注册 artifact-backed MVP dataset。

Request：

```json
{
  "dataset_id": "dataset_demo_001",
  "name": "Demo traffic evaluation set",
  "dataset_type": "artifact_expected_outputs",
  "source": "local_public_or_synthetic",
  "annotation_path": "evals/expected/demo_annotations.json",
  "expected_events_path": "evals/expected/demo_expected_events.jsonl",
  "expected_counts_path": "evals/expected/demo_expected_counts.json",
  "metadata": {}
}
```

Response：

```json
{
  "status": "created",
  "dataset": {}
}
```

Stage：8F。

#### GET /api/evaluation/results

用途：查询 evaluation results。

Query：

- `run_id`: optional string
- `dataset_id`: optional string
- `evaluation_type`: optional string
- `metric_name`: optional string

Response：

```json
{
  "items": [],
  "total": 0
}
```

Stage：8F。

#### POST /api/evaluation/run

用途：启动 artifact-backed MVP evaluation run。

Request：

```json
{
  "run_id": "run_xxx",
  "dataset_id": "dataset_demo_001",
  "evaluation_types": ["event", "flow_counting"],
  "config": {
    "match_window_ms": 1000,
    "iou_threshold": 0.5
  }
}
```

Response：

```json
{
  "status": "completed",
  "evaluation_run_id": "eval_run_xxx",
  "summary_path": "results/traffic_analysis/run_xxx/evaluation_summary.json"
}
```

Stage：8F。

#### GET /api/evaluation/runs

用途：查询 evaluation runs。

Response：

```json
{
  "items": [],
  "total": 0
}
```

Stage：8F。

#### GET /api/evaluation/runs/{evaluation_run_id}

用途：查询 evaluation run 详情。

Response：

```json
{
  "run": {},
  "results": [],
  "failed_cases": []
}
```

Stage：8F。

#### GET /api/evaluation/summary/{run_id}

用途：读取 `results/traffic_analysis/{run_id}/evaluation_summary.json`。

Response：

```json
{
  "schema_version": "stage8.v1",
  "run_id": "run_xxx",
  "summary": {},
  "failed_cases": []
}
```

Stage：8F。

#### GET /api/evaluation/failed-cases

用途：查询 evaluation failed cases。

Query：

- `run_id`: optional string
- `evaluation_run_id`: optional string
- `failure_type`: optional string
- `module`: optional string

Response：

```json
{
  "items": [],
  "total": 0
}
```

Stage：8F。

### 8.3 Review -> Bad Case APIs

#### POST /api/bad-cases/from-review

用途：从 review action 或 false-negative record 创建 Bad Case。

Request：

```json
{
  "run_id": "run_xxx",
  "event_id": "event_xxx",
  "review_id": "review_xxx",
  "case_type": "false_positive",
  "module": "event_engine",
  "root_cause": "direction threshold too sensitive",
  "tags": ["wrong_direction"]
}
```

Response：

```json
{
  "status": "created",
  "case_id": "bc_xxx",
  "case": {}
}
```

备选路由：`POST /api/review/events/{event_id}/bad-case`。Stage 8C 建议先实现 `/api/bad-cases/from-review`，避免把 Bad Case 生命周期塞回 Review API。

### 8.4 Failed Case -> Bad Case APIs

#### POST /api/evaluation/failed-cases/{failed_case_id}/bad-case

用途：从 evaluation failed case 创建 Bad Case。

Request：

```json
{
  "root_cause": "rule threshold too sensitive",
  "tags": ["regression", "wrong_direction"],
  "status": "open"
}
```

Response：

```json
{
  "status": "created",
  "failed_case_id": "fail_xxx",
  "case_id": "bc_xxx",
  "case": {}
}
```

Stage：8H。

## 9. 前端页面草案

### 9.1 BadCaseCenterPage

BadCaseCenterPage MVP 应包含：

- Summary cards：total、open、fixed、verified、ignored、false_positive、false_negative、id_switch、track_lost、rule_error、zone_config_error。
- Bad Case list：case_id、case_type、module、status、run_id、event_id、track_id、frame_index、tags、updated_at。
- Filters：case_type、module、status、tag、run_id。
- Detail panel：description、expected_result、actual_result、root_cause、snapshot_path、linked_review_id、linked_failed_case_id。
- Create Bad Case form：支持手动输入 run/event/track/frame、case_type、module、description、expected/actual、root cause 和 tags。
- Update status：open / fixed / verified / ignored。
- Link to Review：有 `run_id + event_id` 时跳转 `/review?run_id=&event_id=...`。
- Link to Analysis Detail：有 `run_id` 时跳转 `/analysis?run_id=...`。

MVP 不做：

- 批量编辑。
- 多用户权限。
- 高级图片标注。
- 规则重跑。
- 数据库分页优化。

### 9.2 EvaluationCenterPage

EvaluationCenterPage MVP 应包含：

- Evaluation datasets section：展示 dataset_id、name、dataset_type、source、expected paths。
- Evaluation run section：选择 `run_id`、dataset、evaluation types，触发 artifact-backed MVP evaluation。
- Metrics summary cards：按 detection、tracking、trajectory、event、flow_counting、bad_case_regression 分组。
- Failed cases table：failed_case_id、failure_type、module、expected、actual、frame_index、event_id、track_id。
- `evaluation_summary.json` viewer：展示 schema_version、generated_at、summary 和 failed_cases。
- Failed case -> Bad Case link：调用 planned API 创建 Bad Case。
- Warning：明确 MVP metrics 不是工业级完整评测，缺 ground truth 时只显示 diagnostic / planned 状态。

### 9.3 与 Review Center 的跳转关系

Review Center 到 Bad Case：

- 对 false-positive event 提供“Create Bad Case”入口。
- 对 false-negative record 提供“Create Bad Case”入口。
- 创建后展示 `case_id` 和链接。

Bad Case 到 Review Center：

- 通过 `linked_review_id` 或 `run_id + event_id` 返回 Review detail。
- 不修改 Review artifacts。

### 9.4 与 Analysis Detail 的跳转关系

Bad Case / Evaluation failed case 到 Analysis Detail：

- 通过 `run_id` 打开 Analysis Detail。
- 通过 `event_id` 或 `frame_index` 在后续可定位到事件和证据。
- MVP 可先打开 run summary，不强制实现视频 seek。

## 10. scripts 规划

### 10.1 run_evals.py MVP

Stage 8F 才将 `scripts/run_evals.py` 从 placeholder 变为可运行 MVP。

建议 CLI：

```bash
python3 scripts/run_evals.py \
  --run-id run_xxx \
  --dataset-id dataset_demo_001 \
  --types event,flow_counting \
  --results-dir results/traffic_analysis \
  --evals-dir evals
```

MVP 行为：

- 读取 `evals/datasets/evaluation_datasets.json`。
- 校验 `run_id` 对应 run directory 存在。
- 按指定 type 读取 run artifacts 和 expected artifacts。
- 写入 `evals/results/evaluation_runs.jsonl`。
- 写入 `evals/results/evaluation_results.jsonl`。
- 写入 `evals/results/failed_cases.jsonl`。
- 写入 `results/traffic_analysis/{run_id}/evaluation_summary.json`。
- 不下载数据集。
- 不训练模型。
- 不写数据库。

### 10.2 seed_demo_data.py 与 demo eval data

Stage 9 才建议补 demo seed。Stage 8 可只定义 demo evaluation expected files 的格式，不必生成真实视频。

可规划：

- `evals/datasets/evaluation_datasets.json`
- `evals/expected/demo_expected_events.jsonl`
- `evals/expected/demo_expected_counts.json`

这些示例应使用公开数据、模拟配置或小型自建标注，不提交大视频。

### 10.3 evals 目录结构

建议结构：

```text
evals/
  datasets/
    evaluation_datasets.json
  expected/
    demo_expected_events.jsonl
    demo_expected_counts.json
  results/
    evaluation_runs.jsonl
    evaluation_results.jsonl
    failed_cases.jsonl
  scripts/
    README.md
```

Stage 8 开发时仍应避免提交真实大规模 generated results。小型 fixture 可放入测试目录或 docs 示例，不放入 `evals/results/`。

## 11. 测试策略

### 11.1 Bad Case artifact tests

覆盖：

- 空 run 下创建 `bad_cases.jsonl`。
- append-only 写入。
- `case_id` 稳定生成。
- status transition 校验。
- filters by `case_type` / `module` / `status` / `tag`。
- summary counts。
- 无效 `snapshot_path` 被拒绝。

### 11.2 Bad Case API tests

覆盖：

- `GET /api/bad-cases` 空列表。
- `POST /api/bad-cases` 创建。
- `GET /api/bad-cases/{case_id}` 详情。
- `PATCH /api/bad-cases/{case_id}` 更新状态。
- `GET /api/bad-cases/summary` 统计。
- `POST /api/bad-cases/from-review` 从 review artifact 创建。

### 11.3 Evaluation artifact tests

覆盖：

- 读取 dataset config。
- 创建 evaluation run record。
- 写入 result records。
- 写入 failed cases。
- 写入 run-level `evaluation_summary.json`。
- 缺 expected artifact 时返回明确错误。

### 11.4 Metrics unit tests

覆盖：

- event exact/time-window matching。
- event precision/recall/F1 分母为 0。
- flow MAE。
- flow MAPE expected count 为 0。
- bad case regression pass rate。
- metric details 中记录 skipped / unsupported 原因。

### 11.5 Evaluation API tests

覆盖：

- datasets list/create。
- results list。
- `POST /api/evaluation/run` 生成 artifacts。
- evaluation runs list/detail。
- summary by run。
- failed cases list。
- failed case -> bad case。

### 11.6 Frontend utility / build tests

覆盖：

- Bad Case filters utility。
- Bad Case summary counts utility。
- Evaluation metrics summary utility。
- failed case display normalization。
- Review / Analysis link builder。
- `npm run build`。

### 11.7 Regression tests

每个子阶段至少运行：

```bash
git diff --check
python3 -m compileall backend/app
cd backend && ./.venv/bin/python -m pytest
cd ../frontend && node --test tests/analysisRunMetrics.test.mjs
cd ../frontend && node --test tests/reviewMetrics.test.mjs
cd ../frontend && node --test tests/reviewNavigation.test.mjs
cd ../frontend && npm run build -- --outDir /tmp/smarttraffic-vite-build --emptyOutDir
cd .. && docker compose config
python3 scripts/danger_check.py
```

## 12. Stage 8 子阶段拆分

### 12.1 Stage 8A：只读审计 + 设计文档

最小范围：

- 审计当前 Bad Case / Evaluation placeholder。
- 审计 Stage 6/7 artifacts 是否可作为输入。
- 新增本设计文档。
- 不修改后端功能代码。
- 不修改前端功能代码。
- 不修改测试代码。
- 不创建 tag，不 push。

验收：

- `docs/stage8_bad_case_evaluation_design.md` 存在。
- 文档明确 Stage 8 与 Stage 6/7 边界。
- 文档明确 artifact-based MVP 与 DB final 边界。

### 12.2 Stage 8B：Bad Case artifact / schema / service

最小范围：

- 新增 `backend/app/schemas/bad_case.py`。
- 新增 `backend/app/analysis/bad_case_artifacts.py`。
- 扩展 `backend/app/services/bad_case_service.py`，从 placeholder 变为 artifact-backed service。
- 写 `bad_cases.jsonl`。
- 支持 create / list / detail / update / summary 的 service 层。
- 添加 backend tests。

不做：

- 前端页面。
- Evaluation。
- 数据库。

### 12.3 Stage 8C：Bad Case API MVP

最小范围：

- 将 `backend/app/api/bad_cases.py` 从 placeholder 改为真实 API。
- 实现 list、detail、create、patch、summary。
- 实现 from-review API。
- 补 API 文档和测试。

不做：

- 前端页面。
- failed case 转 Bad Case。

### 12.4 Stage 8D：Bad Case Center frontend MVP

最小范围：

- 新增 `frontend/src/api/badCases.ts`。
- 新增 Bad Case types。
- 替换 `BadCaseCenterPage` placeholder。
- 实现 filters、list、detail、create form、status update、summary cards。
- 增加 frontend utility tests。

不做：

- Evaluation UI。
- 图片标注器。

### 12.5 Stage 8E：Evaluation artifact / schema / metrics MVP

最小范围：

- 新增 Evaluation schema。
- 新增 artifact helpers。
- 实现 dataset config 读取。
- 实现 event metrics MVP。
- 实现 flow counting metrics MVP。
- 实现 bad case regression MVP。
- 对 detection/tracking/trajectory 先提供 schema 和 unsupported/diagnostic details，不宣称工业级完整指标。
- 写 artifact/metrics tests。

不做：

- 前端页面。
- 大规模数据集下载器。

### 12.6 Stage 8F：Evaluation API + run_evals.py MVP

最小范围：

- 将 `backend/app/api/evaluation.py` 从 placeholder 改为 artifact-backed API。
- 实现 datasets、results、run、runs、summary、failed-cases。
- 将 `scripts/run_evals.py` 变为可运行 MVP。
- 写 API tests 和脚本 tests。

不做：

- Evaluation Center 前端。
- 数据库。

### 12.7 Stage 8G：Evaluation Center frontend MVP

最小范围：

- 扩展 `frontend/src/api/evaluation.ts`。
- 新增 Evaluation types。
- 替换 `EvaluationCenterPage` placeholder。
- 实现 datasets section、run section、metrics cards、failed cases table、summary viewer。
- 增加 frontend utility tests。

不做：

- 高级图表。
- 复杂对比分析。

### 12.8 Stage 8H：Bad Case / Evaluation 联动与回归 MVP

最小范围：

- 实现 failed case -> Bad Case API。
- Bad Case detail 展示 linked failed case。
- Evaluation failed cases 展示 create/link Bad Case 动作。
- Bad Case regression summary 读取 Bad Case status。
- Review -> Bad Case 与 Evaluation -> Bad Case 两条链路都可验证。

不做：

- 自动改 Review 原始 artifacts。
- 自动改 Bad Case 状态，除非调用 Bad Case API。

### 12.9 Stage 8I：Stage 8 收尾审计、文档、测试、tag

最小范围：

- 更新 README、API reference、architecture、database schema planned/final 边界。
- 确认 Stage 8 artifact-backed MVP 完成。
- 运行全量验证。
- 扫描 generated results、videos、model weights、cache、dist、node_modules。
- 仅在用户明确要求时创建 tag。

不做：

- 自动 push。
- 自动 tag。
- 移动旧 tag。

## 13. 风险与规避

| 风险 | 影响 | 规避 |
| --- | --- | --- |
| 把 Review state 当 Bad Case | 错误资产缺少归因和回归字段 | Bad Case 独立 `bad_cases.jsonl`，只引用 Review artifacts |
| 把 review comments 当 Evaluation report | 指标不可复现 | Evaluation 独立 `evaluation_results.jsonl` 和 `evaluation_summary.json` |
| 缺 ground truth 却宣称工业级指标 | 误导项目状态 | 指标 response 必须声明 unsupported / diagnostic / planned |
| 过早引入数据库 | Stage 8 范围失控 | 先 artifact-backed MVP，DB final 后续迁移 |
| 覆盖原始 Stage 6/7 artifacts | 破坏审计链路 | Stage 8 只追加新 artifacts，不覆盖原始输出 |
| generated eval results 被提交 | 污染仓库 | `.gitignore` + danger check + tracked forbidden scan |
| Bad Case 与 failed case 多对多过早复杂化 | API 和 UI 变重 | MVP 先一对一，后续再建索引 |
| 前端把 placeholder 展示成已完成 | 用户误判阶段 | 页面和文档保留 MVP / planned / unsupported 文案 |

## 14. Stage 8B 最小开发计划

Stage 8B 建议只做 Bad Case artifact / schema / service，不做 API 和前端。

最小开发步骤：

1. 新增 `backend/app/schemas/bad_case.py`，定义 `BadCaseRecord`、`BadCaseCreateRequest`、`BadCaseUpdateRequest`、`BadCaseSummary`。
2. 新增 `backend/app/analysis/bad_case_artifacts.py`，实现 `load_bad_cases`、`append_bad_case`、`update_bad_case`、`summarize_bad_cases`。
3. 更新 `backend/app/services/bad_case_service.py`，使用 artifact helper 提供 service 层方法。
4. 将 `bad_cases.jsonl` artifact summary 小范围接入 manifest / metadata / artifact index，保持 optional。
5. 新增 `backend/tests/test_stage8_bad_case_artifacts.py`。
6. 新增 `backend/tests/test_bad_case_service.py`。
7. 运行 backend tests 和 danger check。
8. 更新本设计文档的 Stage 8B 状态，但仍不声明 Bad Case Center 前端或 Evaluation 完成。

Stage 8B 完成标准：

- 可在 fixture run 下创建、读取、更新和统计 Bad Case。
- `bad_cases.jsonl` append-only 或受控 update 行为有测试覆盖。
- 没有 API 路由变更。
- 没有前端变更。
- 没有 Evaluation 实现。
