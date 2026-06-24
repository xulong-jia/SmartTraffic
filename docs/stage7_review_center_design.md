# Stage 7 Review Center 设计文档

本文档记录 Stage 7A 的只读审计结论和 Stage 7 Review Center 设计草案。当前阶段只做设计，不实现后端 API、前端页面、测试、数据库 migration、Bad Case Center 或 Evaluation Center。

## 1. 阶段目标

Stage 7 的目标是补齐 SmartTraffic 的事件人工复核闭环 MVP，让 Stage 5/6 生成的事件、证据、告警和可视化 artifact 可以被本地复核人员查看、确认、标记和备注。

Stage 7 应完成：

- Review Center MVP。
- 事件复核列表。
- `pending` / `confirmed` / `false_positive` / `false_negative` / `ignored` / `resolved` 事件复核状态流。
- 人工确认事件。
- 标记误报。
- 补充漏报记录的 MVP 设计。
- 复核备注。
- `review_comments` artifact / audit trail。
- Analysis Detail 中进入复核的入口。
- Review Center 页面最小可用。
- Alert 与 Event 的状态关系说明。
- 为 Stage 8 Bad Case 预留关联入口，但不正式实现 Bad Case。

Stage 7 的实现口径仍是 artifact-based MVP。它应复用 Stage 6 的 Analysis Runs、events、alerts、keyframes、annotated video 和 artifact manifest，不引入真实数据库作为必须依赖。

## 2. 非目标

Stage 7 暂不做：

- 不做正式 Bad Case Center。
- 不做 Evaluation Center。
- 不做评测指标。
- 不做真实数据库 migration。
- 不做权限系统。
- 不做多用户审计。
- 不做复杂工作流引擎。
- 不做规则重跑。
- 不做自动修复。
- 不做生产级审计合规。
- 不做实时流。
- 不做模型训练。

Stage 7 也不改变 Stage 5/6 的事件规则、告警生成、交通统计和可视化 artifact 生成逻辑。Review Center 只消费已有结果并写入复核 artifact。

## 3. 当前基础审计

### 3.1 已有能力

当前 Stage 1-6 已提供以下可复用能力：

- `EventService` 基于 trajectory artifacts 运行 Event Engine，写入 `events.jsonl`、`event_evidence.jsonl`、`rule_executions.jsonl` 和 `event_summary.json`。
- `AlertService` 基于事件 artifact 生成 `alerts.jsonl` 和 `alert_summary.json`，并支持 artifact-backed 告警状态更新。
- `TrafficAnalysisService` 可按 `run_id` 读取 run summary、events、event evidence、rule executions、alerts、flow counts、zone statistics、keyframes 和 annotated video artifact 状态。
- `GET /api/analysis-runs/{run_id}/events` 已能读取 Stage 6 event artifacts。
- `GET /api/analysis-runs/{run_id}/alerts` 已能读取 Stage 6 alert artifacts。
- `GET /api/alerts`、`GET /api/alerts/{alert_id}`、`PATCH /api/alerts/{alert_id}/acknowledge`、`PATCH /api/alerts/{alert_id}/resolve`、`PATCH /api/alerts/{alert_id}/ignore` 已存在，并写回当前 artifact-backed alert storage。
- 前端 `AnalysisDetailPage` 已展示 events、event evidence、rule executions 和 alerts。
- 前端 `AlertCenterPage` 已支持 run/status/level 过滤和 acknowledge / resolve / ignore 告警操作。
- 前端导航已有 `Review Center (planned)`、`Bad Case Center (planned)` 和 `Evaluation Center (planned)` 入口。
- Stage 6 visual artifacts 已包含 keyframes index、keyframe snapshots 和 `annotated_video.mp4` 的 manifest 状态，可作为人工复核证据入口。

### 3.2 部分能力

当前已有一些 Stage 7 可复用但尚未形成 Review Center 的能力：

- `backend/app/events/contracts.py` 已定义事件状态集合：`pending`、`confirmed`、`false_positive`、`false_negative`、`ignored`、`resolved`。
- 新生成事件默认状态为 `pending`。
- `frontend/src/types/index.ts` 中 `TrafficEvent` 已允许 `status` 字段，但没有独立 review state 类型。
- `AlertRecord` 中存在 `event_id`，可建立 alert 到 event 的跳转关系。
- Stage 6 manifest / artifact index 能表达 artifact 可用、缺失、空结果、错误和 planned 状态，可复用于 Review Center 的证据状态展示。

这些能力只代表 contract 或读取基础，不代表复核功能已经实现。

### 3.3 未实现能力

当前未实现：

- `/api/review/events` 真实查询逻辑。当前 `backend/app/api/review.py` 只返回 placeholder。
- standalone `/api/events` 真实查询逻辑。当前 `backend/app/api/events.py` 只返回 placeholder。
- `ReviewService` 真实业务逻辑。当前 `backend/app/services/review_service.py` 仍是 placeholder。
- review schemas，例如 review event response、review action request、review comment response。
- `review_comments.jsonl` artifact。
- `review_state.json` 或 `event_review_state.json` 派生状态 artifact。
- `false_negative_events.jsonl` artifact。
- 事件确认、误报标记、漏报补充、忽略、解决和备注写入能力。
- before/after status 审计留痕。
- Review Center 可用前端页面。当前 `ReviewCenterPage` 是 placeholder，并只渲染 `EventTable` contract。
- Analysis Detail 中的 event review 入口、review status、comments count。
- Alert Center 到关联 event review 的跳转。
- Bad Case 管理中心、Evaluation Center 和评测报告。

### 3.4 当前风险

进入 Stage 7B 前需要控制以下风险：

- 事件复核状态和告警处理状态容易混淆。`alert.status=resolved` 不等于 `event.status=confirmed` 或 `event.status=resolved`。
- 如果直接覆盖 `events.jsonl`，会破坏 Stage 5/6 的原始事件输出，不利于审计和回归。
- `false_negative` 没有原始 `event_id`，需要独立 artifact 和临时 ID 策略，不能强行伪装成 Event Engine 输出。
- `review_comments` 是审计留痕，不应被当成 Evaluation report 或 Bad Case 数据库。
- Stage 7 可以预留 `bad_case_id` / `bad_case_link` 字段，但不能在本阶段宣称 Bad Case Center 已完成。
- artifact-backed MVP 需要定义并发写入和文件损坏的最小防护，避免局部写失败破坏整个 run 的可读性。

## 4. Review Center 总体设计

### 4.1 Review Center 的职责

Review Center 负责围绕一次 `run_id` 的事件结果提供人工复核能力：

- 读取 Stage 6 事件、证据、规则执行、告警和可视化 artifact。
- 展示待复核事件列表，默认优先 `pending`。
- 展示事件详情、证据摘要、关联告警、keyframes / annotated video artifact 状态。
- 写入事件复核动作和备注。
- 维护事件的派生 review state。
- 记录每次状态变更的 before/after status、reviewer、comment、source 和 timestamp。
- 允许新增漏报记录 MVP，并将其作为 review artifact 保存。

Review Center 的输出是复核状态和审计留痕，不重新计算 Event Engine，不改变检测、跟踪、轨迹或规则执行输出。

### 4.2 与 Event Engine 的边界

Event Engine 负责根据轨迹点、区域和规则生成事件。它输出的 `events.jsonl`、`event_evidence.jsonl` 和 `rule_executions.jsonl` 是算法/规则结果。

Review Center 只在这些结果之上写入人工判断：

- 不重跑规则。
- 不修改 Event Engine rule callback。
- 不修改原始 event evidence。
- 不把人工备注写回 rule execution。
- 不把人工复核状态作为 Event Engine 的输入条件。

如果需要展示最终复核状态，应在读取时将 `events.jsonl` 与 `event_review_state.json` 合并，形成 derived view。

### 4.3 与 Alert Center 的边界

Alert Center 负责告警处理状态，当前支持：

- `new`
- `acknowledged`
- `resolved`
- `ignored`

Review Center 负责事件正确性状态，设计状态为：

- `pending`
- `confirmed`
- `false_positive`
- `false_negative`
- `ignored`
- `resolved`

两者关系：

- 一个 alert 通常关联一个 `event_id`。
- alert 被 acknowledge 只表示有人看到或接手告警，不表示事件真实。
- alert 被 resolved 只表示告警处理闭环，不表示事件已被确认。
- event 被 false_positive 不应自动删除 alert，但 Review Center 可提示相关 alert 需要同步处理。
- event 被 confirmed 不应自动 resolved alert，除非后续阶段设计明确联动策略。
- Stage 7 MVP 可以提供 Alert Center 到 event review 的跳转，但不做复杂状态联动。

### 4.4 与 Traffic Analysis Center 的边界

Traffic Analysis Center 是 Stage 6 的结果读取底座，负责按 `run_id` 组织和读取：

- detections
- tracks
- trajectory points
- events
- alerts
- flow counts
- zone statistics
- manifest
- artifact index
- keyframes
- annotated video

Review Center 应复用这些读取能力，并在同一 run directory 下追加 review artifacts。Traffic Analysis Center 不负责解释人工复核动作，也不应把 Review Center 变成结果索引的一部分。后续可以在 run summary 中增加只读 `review_artifacts` 或 `review_status` 摘要，但该摘要必须来自 Review Center artifact。

### 4.5 与 Bad Case / Evaluation 的边界

Stage 7 的重点是人工复核事件状态和备注。

Stage 7 可以预留 Bad Case 入口，但不实现 Bad Case 管理中心。Stage 8 才正式做 Bad Case Center 和 Evaluation Center。

边界要求：

- Stage 7 的 `false_positive` / `false_negative` 状态不等于 Stage 8 的完整 Bad Case 回归体系。
- Stage 7 的 review comments 是审计留痕，不等于 Evaluation report。
- Stage 7 不计算 precision、recall、false positive rate、false negative rate 或 regression pass rate。
- Stage 7 不创建完整 `bad_cases` 生命周期，不维护 case root cause、修复状态或回归结果。
- Stage 7 可在 review record 中预留 `bad_case_id`、`bad_case_link`、`future_bad_case_candidate` 字段，但这些字段只能是 future link，不代表 Bad Case 已实现。

## 5. Review 状态模型

### 5.1 Event status

Stage 7 事件复核状态建议沿用现有 `EVENT_STATUSES`：

| status | 语义 |
| --- | --- |
| `pending` | 系统生成事件后尚未人工复核。 |
| `confirmed` | 复核人员确认事件真实且规则判断可接受。 |
| `false_positive` | 系统报出事件，但复核认为实际不是该事件。 |
| `false_negative` | 实际存在事件，但系统没有生成对应事件。 |
| `ignored` | 复核人员决定不处理该事件，例如样本无效、场景不适用或证据不足。 |
| `resolved` | 事件复核处理已闭环，通常用于后续流程或运营语义，不等同于告警 resolved。 |

`pending` 应来自原始 event 的默认状态或没有 review state 时的派生默认值。其他状态应来自 `event_review_state.json` 或 `false_negative_events.jsonl`。

### 5.2 Review action

Stage 7 MVP 建议支持以下 action：

| action | before_status | after_status | 说明 |
| --- | --- | --- | --- |
| `confirm` | `pending` / `ignored` / `false_positive` / `resolved` | `confirmed` | 人工确认事件。 |
| `mark_false_positive` | `pending` / `confirmed` / `resolved` | `false_positive` | 标记误报。 |
| `add_false_negative` | null | `false_negative` | 补充系统漏报记录。 |
| `ignore` | `pending` / `confirmed` / `false_positive` | `ignored` | 忽略事件。 |
| `resolve` | `pending` / `confirmed` / `false_positive` / `ignored` | `resolved` | 标记复核处理已闭环。 |
| `comment` | current status | current status | 只添加备注，不改变状态。 |

状态流转规则在 MVP 中可以保持宽松，但必须记录 before/after。若请求的 before status 与当前派生状态不一致，API 应返回 409，避免覆盖他人操作或旧页面提交。

### 5.3 Alert status 与 Event review status 的关系

Alert status 是告警处理状态，Event review status 是事件正确性状态。它们可以互相引用，但不自动等价。

建议 Stage 7 MVP 关系：

- Review event response 可包含 `linked_alerts`。
- Alert response 可在前端生成 `review_url` 或 `review_target`，指向 `run_id + event_id`。
- Review action 不自动调用 `PATCH /api/alerts/{alert_id}/resolve`。
- Alert action 不自动调用 review confirm / false positive。
- 后续若要联动，需要单独设计明确的策略和测试。

### 5.4 false_positive / false_negative 语义

`false_positive` 表示系统产生了事件，但人工认为它不应作为有效事件成立。该状态必须引用已有 `event_id`。

`false_negative` 表示实际存在事件，但系统没有产生对应事件。该状态通常没有原始 `event_id`，应由 Review Center 创建 `review_event_id` 或 `false_negative_id`，并记录：

- `run_id`
- `event_type`
- `expected_status=false_negative`
- `frame_index` 或 `start_frame` / `end_frame`
- `timestamp_ms` 或 `start_time_ms` / `end_time_ms`
- `track_id` 可选
- `zone_id` 可选
- `evidence` 可选
- `comment`
- `reviewer`

这些 false-negative records 是 Stage 7 review artifacts，不是 Stage 8 bad cases，也不是 Evaluation Center 的 ground truth。

## 6. Artifact 设计

### 6.1 review_comments.jsonl

`review_comments.jsonl` 是 Stage 7 的核心审计留痕 artifact。它应位于对应 run directory 下，例如：

```text
results/traffic_analysis/{run_id}/review_comments.jsonl
```

建议单条结构：

```json
{
  "review_id": "review_...",
  "run_id": "run_...",
  "event_id": "event_...",
  "alert_id": null,
  "action": "confirm",
  "before_status": "pending",
  "after_status": "confirmed",
  "comment": "Reviewer confirmed the event.",
  "reviewer": "local_reviewer",
  "created_at": "2026-06-25T00:00:00+00:00",
  "source": "review_center",
  "bad_case_id": null,
  "bad_case_link": null,
  "future_bad_case_candidate": false
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `review_id` | 是 | 单条 review action 的稳定 ID。 |
| `run_id` | 是 | 所属分析 run。 |
| `event_id` | 否 | 已有事件 ID；漏报记录可为空或指向 synthetic ID。 |
| `alert_id` | 否 | 关联告警 ID。 |
| `action` | 是 | `confirm`、`mark_false_positive`、`add_false_negative`、`ignore`、`resolve`、`comment`。 |
| `before_status` | 否 | 操作前派生事件状态。漏报新增可为 null。 |
| `after_status` | 是 | 操作后派生事件状态。纯 comment 可与 before 相同。 |
| `comment` | 否 | 复核备注。 |
| `reviewer` | 是 | MVP 可使用本地输入值或 `local_reviewer` 默认值。 |
| `created_at` | 是 | UTC ISO timestamp。 |
| `source` | 是 | `review_center`、`analysis_detail` 或 `alert_center`。 |
| `bad_case_id` | 否 | Stage 8 预留字段。 |
| `bad_case_link` | 否 | Stage 8 预留字段。 |
| `future_bad_case_candidate` | 否 | 是否建议后续进入 Bad Case。 |

`review_comments.jsonl` 只追加，不覆盖。每次状态变更都必须追加一条记录。

### 6.2 review_state.json

为避免破坏原始 `events.jsonl`，Stage 7 MVP 应引入派生状态 artifact。推荐文件名为：

```text
results/traffic_analysis/{run_id}/event_review_state.json
```

也可命名为 `review_state.json`，但建议字段明确以 event 为 key：

```json
{
  "schema_version": "stage7_review_state.v1",
  "run_id": "run_...",
  "updated_at": "2026-06-25T00:00:00+00:00",
  "events": {
    "event_abc": {
      "event_id": "event_abc",
      "status": "confirmed",
      "last_review_id": "review_...",
      "last_action": "confirm",
      "reviewer": "local_reviewer",
      "updated_at": "2026-06-25T00:00:00+00:00",
      "comments_count": 2,
      "linked_alert_ids": ["alert_abc"],
      "bad_case_id": null,
      "future_bad_case_candidate": false
    }
  }
}
```

读取事件列表时，Review API 应按以下顺序合并状态：

1. 读取 `events.jsonl` 原始事件。
2. 读取 `event_review_state.json`。
3. 对每个原始 event 用 review state 覆盖展示用 `status`、`comments_count`、`last_reviewed_at` 等字段。
4. 原始 `events.jsonl` 不被覆盖。

`event_review_state.json` 是当前状态索引，`review_comments.jsonl` 是审计历史。若两者不一致，应以 `review_comments.jsonl` 可重放结果为准，并在后续维护命令中重建 state。

### 6.3 false_negative_events.jsonl

漏报记录建议独立保存：

```text
results/traffic_analysis/{run_id}/false_negative_events.jsonl
```

建议单条结构：

```json
{
  "false_negative_id": "fn_...",
  "run_id": "run_...",
  "event_type": "wrong_way_driving",
  "status": "false_negative",
  "track_id": 12,
  "zone_id": "zone_1",
  "start_frame": 100,
  "end_frame": 130,
  "start_time_ms": 4000,
  "end_time_ms": 5200,
  "evidence": {
    "description": "Manual reviewer observed wrong-way movement."
  },
  "comment": "Missed by current rule.",
  "reviewer": "local_reviewer",
  "created_at": "2026-06-25T00:00:00+00:00",
  "source": "review_center",
  "bad_case_id": null,
  "future_bad_case_candidate": true
}
```

新增漏报时应同时追加：

- 一条 `false_negative_events.jsonl` record。
- 一条 `review_comments.jsonl` action=`add_false_negative` record。
- 一条 `event_review_state.json` synthetic event state，方便列表展示。

### 6.4 与 events.jsonl 的关系

`events.jsonl` 是 Event Engine 原始输出。Stage 7 不应直接修改它。

Review API 的展示层可以返回合并后的 `review_status` 或覆盖后的展示 `status`，但 response 中应保留原始状态来源：

```json
{
  "event_id": "event_...",
  "original_status": "pending",
  "review_status": "confirmed",
  "status": "confirmed",
  "status_source": "event_review_state",
  "comments_count": 1
}
```

这样可以同时满足 UI 简洁展示和审计可追溯。

### 6.5 与 alerts.jsonl 的关系

`alerts.jsonl` 是 Alert Center 的告警 artifact。Stage 7 不应为了事件复核直接修改 alert status。

Review API 可以按 `event_id` 聚合关联 alert：

```json
{
  "linked_alerts": [
    {
      "alert_id": "alert_...",
      "status": "new",
      "level": "critical",
      "message": "Wrong way event detected"
    }
  ]
}
```

若复核动作来自 Alert Center 入口，可在 `review_comments.jsonl` 中记录 `alert_id` 和 `source=alert_center`。

### 6.6 与 keyframes / annotated_video 的关系

Stage 6F 的 keyframes 和 annotated video 是人工复核的证据入口，不是复核结果。

Review API 可在 event detail 中返回 artifact availability：

```json
{
  "visual_artifacts": {
    "keyframes": {
      "status": "available",
      "index_path": "keyframes/index.json",
      "items": []
    },
    "annotated_video": {
      "status": "available",
      "path": "annotated_video.mp4"
    }
  }
}
```

MVP 只需展示 artifact status 和可用路径，不实现复杂视频 overlay editor。

## 7. API Contract 草案

本节是草案，不代表当前已实现。

通用错误：

| 状态码 | 场景 |
| --- | --- |
| 400 | request 参数非法、status/action 不支持、必填字段缺失。 |
| 404 | run、event、alert 或 review record 不存在。 |
| 409 | `before_status` 与当前派生状态不一致，或重复创建冲突。 |
| 422 | schema validation failed。 |
| 500 | artifact 读取/写入失败。 |

所有写接口 MVP 只写 local artifacts，不写数据库。DB final 版本可在后续迁移到 `review_comments`、`events.status` 或独立 `event_review_state` 表，但不得改变 API 的核心语义。

### 7.1 GET /api/review/events

用途：查询某个 run 下的待复核或已复核事件列表。

Query parameters：

- `run_id`: required。
- `status`: optional，支持 `pending`、`confirmed`、`false_positive`、`false_negative`、`ignored`、`resolved`。
- `event_type`: optional。
- `track_id`: optional integer。
- `alert_id`: optional，用于从告警跳转定位。
- `include_false_negatives`: optional boolean，默认 true。
- `limit`: optional integer，默认 100。
- `offset`: optional integer，默认 0。

Response schema：

```json
{
  "run_id": "run_...",
  "items": [
    {
      "event_id": "event_...",
      "event_type": "wrong_way_driving",
      "severity": "high",
      "track_id": 12,
      "zone_id": "zone_1",
      "start_frame": 100,
      "end_frame": 130,
      "original_status": "pending",
      "review_status": "confirmed",
      "status": "confirmed",
      "status_source": "event_review_state",
      "comments_count": 1,
      "linked_alert_count": 1,
      "last_reviewed_at": "2026-06-25T00:00:00+00:00",
      "is_false_negative": false
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

读取逻辑：

- 从 Stage 6 `events.jsonl` 读取原始事件。
- 从 `event_review_state.json` 合并派生状态。
- 从 `false_negative_events.jsonl` 追加漏报记录。
- 从 `alerts.jsonl` 汇总 linked alert count。
- 从 `review_comments.jsonl` 计算 comments count。

### 7.2 GET /api/review/events/{event_id}

用途：读取单个事件复核详情。

Query parameters：

- `run_id`: required。
- `include_comments`: optional boolean，默认 true。
- `include_alerts`: optional boolean，默认 true。
- `include_visual_artifacts`: optional boolean，默认 true。

Response schema：

```json
{
  "run_id": "run_...",
  "event": {
    "event_id": "event_...",
    "event_type": "wrong_way_driving",
    "original_status": "pending",
    "review_status": "confirmed",
    "status": "confirmed",
    "evidence": {},
    "rule_execution_ids": []
  },
  "event_evidence": [],
  "rule_executions": [],
  "linked_alerts": [],
  "comments": [],
  "visual_artifacts": {
    "keyframes": {"status": "available"},
    "annotated_video": {"status": "available"}
  }
}
```

错误：

- run 不存在：404。
- event 不存在且不是 false-negative synthetic event：404。
- event artifacts 缺失：404 或 500，按现有 Analysis Runs 行为对齐。

### 7.3 POST /api/review/events/{event_id}/confirm

用途：确认已有事件。

Query parameters：

- `run_id`: required。

Request body：

```json
{
  "before_status": "pending",
  "comment": "Confirmed after checking keyframes.",
  "reviewer": "local_reviewer",
  "alert_id": null,
  "source": "review_center"
}
```

Response schema：

```json
{
  "run_id": "run_...",
  "event_id": "event_...",
  "status": "confirmed",
  "review_id": "review_...",
  "comment": "Confirmed after checking keyframes.",
  "updated_at": "2026-06-25T00:00:00+00:00"
}
```

写入逻辑：

- 校验 event 存在于 `events.jsonl`。
- 读取当前派生状态。
- 校验 `before_status`。
- 追加 `review_comments.jsonl` action=`confirm`。
- 更新 `event_review_state.json`。

### 7.4 POST /api/review/events/{event_id}/false-positive

用途：标记已有事件为误报。

Query parameters：

- `run_id`: required。

Request body：

```json
{
  "before_status": "pending",
  "comment": "Vehicle did not enter the configured zone.",
  "reviewer": "local_reviewer",
  "alert_id": "alert_...",
  "source": "review_center",
  "future_bad_case_candidate": true
}
```

Response schema：

```json
{
  "run_id": "run_...",
  "event_id": "event_...",
  "status": "false_positive",
  "review_id": "review_...",
  "future_bad_case_candidate": true
}
```

写入逻辑与 confirm 相同，但 action=`mark_false_positive`、after_status=`false_positive`。

### 7.5 POST /api/review/events/{event_id}/ignore

用途：忽略已有事件。

Request body：

```json
{
  "run_id": "run_...",
  "before_status": "pending",
  "comment": "Scene is outside review scope.",
  "reviewer": "local_reviewer",
  "source": "review_center"
}
```

Response schema：

```json
{
  "run_id": "run_...",
  "event_id": "event_...",
  "status": "ignored",
  "review_id": "review_..."
}
```

### 7.6 POST /api/review/events/{event_id}/resolve

用途：标记事件复核处理已闭环。

Request body：

```json
{
  "run_id": "run_...",
  "before_status": "confirmed",
  "comment": "Review is complete.",
  "reviewer": "local_reviewer",
  "source": "review_center"
}
```

Response schema：

```json
{
  "run_id": "run_...",
  "event_id": "event_...",
  "status": "resolved",
  "review_id": "review_..."
}
```

注意：event resolved 不自动 resolve alert。

### 7.7 POST /api/review/false-negatives

用途：新增漏报记录 MVP。

Request body：

```json
{
  "run_id": "run_...",
  "event_type": "wrong_way_driving",
  "track_id": 12,
  "zone_id": "zone_1",
  "start_frame": 100,
  "end_frame": 130,
  "start_time_ms": 4000,
  "end_time_ms": 5200,
  "evidence": {
    "description": "Manual reviewer observed a missed event."
  },
  "comment": "Missed by current rule.",
  "reviewer": "local_reviewer",
  "source": "review_center",
  "future_bad_case_candidate": true
}
```

Response schema：

```json
{
  "run_id": "run_...",
  "false_negative_id": "fn_...",
  "event_id": "fn_...",
  "status": "false_negative",
  "review_id": "review_..."
}
```

写入逻辑：

- 校验 run 存在。
- 可选校验 frame/time 范围在 run metadata 中可解释。
- 追加 `false_negative_events.jsonl`。
- 追加 `review_comments.jsonl` action=`add_false_negative`。
- 更新 `event_review_state.json` synthetic event state。

### 7.8 POST /api/review/comments

用途：添加复核备注，不一定改变状态。

Request body：

```json
{
  "run_id": "run_...",
  "event_id": "event_...",
  "alert_id": null,
  "comment": "Need second reviewer later.",
  "reviewer": "local_reviewer",
  "source": "review_center"
}
```

Response schema：

```json
{
  "review_id": "review_...",
  "run_id": "run_...",
  "event_id": "event_...",
  "action": "comment",
  "before_status": "confirmed",
  "after_status": "confirmed",
  "created_at": "2026-06-25T00:00:00+00:00"
}
```

写入逻辑：

- 校验 run 和 event 或 false-negative synthetic event 存在。
- 获取当前派生状态。
- 追加 `review_comments.jsonl` action=`comment`。
- 更新 `event_review_state.json.comments_count` 和 `updated_at`。

### 7.9 GET /api/review/comments

用途：查询复核备注和审计历史。

Query parameters：

- `run_id`: required。
- `event_id`: optional。
- `alert_id`: optional。
- `action`: optional。
- `reviewer`: optional。
- `limit`: optional integer，默认 100。
- `offset`: optional integer，默认 0。

Response schema：

```json
{
  "run_id": "run_...",
  "items": [
    {
      "review_id": "review_...",
      "event_id": "event_...",
      "alert_id": null,
      "action": "confirm",
      "before_status": "pending",
      "after_status": "confirmed",
      "comment": "Reviewer confirmed the event.",
      "reviewer": "local_reviewer",
      "created_at": "2026-06-25T00:00:00+00:00",
      "source": "review_center"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

读取逻辑：

- 从 `review_comments.jsonl` 读取。
- 支持按 event、alert、action、reviewer 过滤。
- 只返回当前 run 的数据。

## 8. 前端页面草案

### 8.1 ReviewCenterPage

ReviewCenterPage MVP 应是一个简单工作台，不做复杂 UI。

建议组成：

- 顶部筛选：`run_id` input、status select、event_type select、track_id input、Refresh。
- Pending events 列表：默认 status=`pending`，展示 severity、event type、track、zone、frame/time、linked alert count、comments count、last reviewed。
- Event detail panel / drawer：选择事件后展示详情，不需要新页面路由。
- Evidence summary：展示 event evidence、rule execution 摘要和关键字段。
- Linked alert summary：展示关联 alert 的 status、level、message 和 alert action 状态。
- Visual artifact status：展示 keyframes / annotated video 是否 available、missing、planned、empty、error。
- 操作按钮：Confirm、Mark false positive、Ignore、Resolve。
- Comment form：reviewer、comment、source，提交后刷新 comments。
- Add false negative form MVP：run_id、event_type、track_id、zone_id、frame/time、comment。
- 空状态：无事件、无 comments、无 visual artifacts 时给出简短说明。
- 错误状态：API 请求失败或 artifact 缺失时显示错误，不隐藏当前筛选。
- 加载状态：列表和 detail 独立 loading，避免整页闪烁。

ReviewCenterPage 不应实现 Bad Case 管理表、Evaluation charts、规则重跑或视频编辑器。

### 8.2 AnalysisDetailPage review 入口

未来增强：

- Event 表格中每个 event 增加 `Review` 入口。
- 显示 `review_status` 或合并后的 `status`。
- 显示 `comments_count`。
- 如果 keyframes / annotated video available，可提供跳转到 Review detail 的上下文。
- 入口参数至少包含 `run_id` 和 `event_id`。

Analysis Detail 仍主要负责结果浏览，不应复制完整 Review Center 工作台。

### 8.3 AlertCenterPage 跳转 review

未来增强：

- Alert 行增加 `Review event` 入口，使用 `run_id + event_id` 定位 Review Center detail。
- Alert detail 可展示当前 event review status。
- Alert resolve 与 event review status 保持边界：alert resolve 不自动确认事件，event false_positive 不自动关闭告警。
- 如果 alert 缺少 event_id，应显示不可跳转状态。

### 8.4 空状态 / 错误状态 / 加载状态

Review Center 需要覆盖以下 UI 状态：

- 未输入 `run_id`：提示输入 run id 或从 Analysis Detail / Alert Center 进入。
- run 不存在：显示 404 说明。
- run 存在但没有 event artifacts：显示 events artifact missing。
- run 存在且 events 为空：显示 no events。
- status filter 无匹配：显示 no events match filters。
- review artifacts 不存在：视为尚未复核，不作为错误。
- review artifact JSON 损坏：显示错误，并阻止写入直到修复或重建。
- 提交中：禁用当前 action button，避免重复写入。

## 9. 测试策略

### 9.1 Review artifact 测试

Stage 7B 应先覆盖 artifact 层：

- 空 run 下初始化 `review_comments.jsonl` 和 `event_review_state.json`。
- confirm action 追加 review comment 并更新 state。
- mark_false_positive action 记录 before/after。
- comment action 不改变 status 但增加 comments count。
- add_false_negative 同时写入 `false_negative_events.jsonl`、`review_comments.jsonl` 和 state。
- 损坏 JSON / JSONL 行的错误处理。
- 不修改原始 `events.jsonl`。

### 9.2 Review API 测试

API 测试应覆盖：

- `GET /api/review/events?run_id=...` 合并原始 events 和 review state。
- status / event_type / track_id / alert_id filters。
- `GET /api/review/events/{event_id}` 返回 evidence、rule executions、linked alerts、comments 和 visual artifact status。
- confirm / false-positive / ignore / resolve 写接口。
- false-negative create。
- comments create/list。
- 404 run not found、404 event not found、409 before_status mismatch、400 unsupported status/action。

### 9.3 Event status transition 测试

状态测试应覆盖：

- pending -> confirmed。
- pending -> false_positive。
- confirmed -> resolved。
- pending -> ignored。
- comment 保持当前 status。
- before_status 不匹配时拒绝。
- false_negative synthetic event 不要求存在于 `events.jsonl`。

MVP 可以允许较宽松的状态切换，但必须测试所有 action 的 before/after 审计记录。

### 9.4 前端 build / utility 测试

前端测试建议：

- Review API client query params 构建。
- ReviewCenterPage 空 run、loading、error、empty states。
- 事件列表渲染 status、linked alert count、comments count。
- action button 调用对应 client 并刷新列表。
- comment form basic validation。
- add false negative form basic validation。
- TypeScript build 和 Vite build。

### 9.5 回归测试

Stage 7 每个子阶段至少运行：

- `git diff --check`
- `python3 -m compileall backend/app`
- 后端 pytest
- 前端轻量测试
- 前端 build
- `docker compose config`
- `python3 scripts/danger_check.py`
- 大文件 / 敏感词 / tracked forbidden file 扫描

新增 review artifacts、fixtures 或 screenshots 时必须确认不会提交 generated results、videos、model weights、cache、dist、node_modules。

## 10. Stage 7 子阶段拆分

### 10.1 Stage 7B：Review artifact 与状态模型

目标：

- 新增 review artifact helper / service skeleton。
- 定义 review record、review state、false negative record schema。
- 支持 artifact read/write 的最小逻辑。
- 不接入前端。

验收：

- 可对 fixture run 执行 confirm、false_positive、ignore、resolve、comment、add_false_negative。
- `events.jsonl` 不被修改。
- artifact 单元测试通过。

### 10.2 Stage 7C：Review API MVP

目标：

- 实现本设计中的 Review API MVP。
- 与 Stage 6 events / alerts / visual artifacts 读取打通。
- 保持 Bad Case / Evaluation 不实现。

验收：

- Review API 测试覆盖读取、写入、错误状态和 before_status conflict。
- `/api/review/events` 不再是 placeholder。

### 10.3 Stage 7D：Review Center 前端 MVP

目标：

- 实现 ReviewCenterPage 的列表、详情、action 和 comment MVP。
- 新增前端 review API client 和 types。
- 保持 UI 简洁，不做复杂视频编辑或 Bad Case 页面。

验收：

- 前端轻量测试和 build 通过。
- 无 run、无事件、artifact 缺失、提交失败等状态可见。

### 10.4 Stage 7E：Analysis / Alert 联动

目标：

- AnalysisDetailPage 增加 Review 入口、review status、comments count。
- AlertCenterPage 增加关联 event review 跳转。
- 明确 alert status 与 event review status 不自动联动。

验收：

- 从 Analysis Detail 和 Alert Center 可定位 Review Center 的 run/event。
- 不破坏现有 Alert Center 状态操作。

### 10.5 Stage 7F：Stage 7 收尾审计、文档、测试、tag

目标：

- 完成 Stage 7 文档收尾。
- 更新 README / API reference 的实现边界。
- 跑全量回归。
- 在用户明确要求时再创建 Stage 7 tag。

验收：

- Review Center artifact-based MVP 明确完成。
- Bad Case / Evaluation 仍标记为后续阶段。
- 旧 tag 不移动。

## 11. 风险与规避

| 风险 | 规避 |
| --- | --- |
| 直接覆盖 `events.jsonl` 破坏原始结果 | 使用 `event_review_state.json` 派生状态，`review_comments.jsonl` 保留历史。 |
| alert status 与 event status 混淆 | API 和 UI 使用不同字段名，并在文档中明确不自动联动。 |
| false_negative 缺少原始 event | 使用 `false_negative_events.jsonl` 和 synthetic ID。 |
| Stage 7 被误认为 Bad Case/Evaluation 完成 | 只预留 future link，不创建 Bad Case lifecycle，不计算 metrics。 |
| JSONL 追加失败或 state 写坏 | 写入时先追加 audit，再原子更新 state；失败时可通过 audit replay 重建 state。 |
| 多窗口重复提交 | request 带 `before_status`，不一致返回 409。 |
| generated artifacts 被提交 | danger check 和 forbidden file scan 保持为每阶段收尾项。 |

## 12. Stage 7B 最小开发计划

Stage 7B 建议采用小步实现：

1. 新增 review artifact schema / constants，复用现有 event status 枚举。
2. 新增 artifact path resolver，只定位 `results/traffic_analysis/{run_id}` 下的 review files。
3. 实现读取当前事件派生状态：原始 event status + `event_review_state.json`。
4. 实现 append-only `review_comments.jsonl` writer。
5. 实现 `event_review_state.json` 原子更新。
6. 实现 `false_negative_events.jsonl` writer。
7. 增加 artifact 单元测试，确认不修改 `events.jsonl`。
8. 更新 Stage 7B 文档或 API reference 的 planned/implemented 边界。

Stage 7B 完成后仍不需要实现前端 Review Center。前端应放到 Stage 7D，Analysis / Alert 联动应放到 Stage 7E。
