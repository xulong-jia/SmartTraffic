# Stage 6 Traffic Analysis Center 设计文档

本文档最初是 Stage 6A 的只读审计与设计准备文档。Stage 6B 已在 artifact-based / in-memory MVP 范围内实现 run manifest 与 artifact index 加固；Stage 6C 已实现 artifact-backed `flow_counts.json` 和 `zone_statistics.json` MVP；本文档继续记录 Stage 6 的目标边界和后续子阶段。

## 1. 阶段目标

Stage 6 的目标是把一次视频分析的结果按 `run_id` 统一管理，形成可由后端 API、Dashboard、后续 Review Center 和 Evaluation Center 读取的结果底座。

Stage 6 要做：

- 标准化 `results/traffic_analysis/<run_id>/` 结果目录。
- 加固 `metadata.json`，明确 run、video、配置快照、处理阶段和产物状态。
- 引入 artifact manifest / artifact index，使前端和后续模块可以判断每个产物是否存在、是否可读、是否属于可选产物。
- 在已有 detections、tracks、trajectory_points、events、alerts 产物基础上，补齐 Stage 6 聚合产物 `flow_counts.json` 和 `zone_statistics.json`。
- 增强 Analysis Runs API，使 run summary、artifact manifest、detections、tracks、trajectory points、events、alerts、flow counts、zone statistics 都有稳定读取入口。
- 让前端 Dashboard、Video Center、Analysis Detail 逐步读取真实 run 结果。
- 设计 keyframes 和 annotated_video 的产物契约，为后续 Stage 6F 实现预留路径。
- 为 Stage 7 Review Center 和 Stage 8 Evaluation Center 提供统一数据底座，但不在 Stage 6 中实现复核或评估业务。

## 2. 非目标

Stage 6 暂不做：

- 不做 Review Center 事件复核。
- 不做 Bad Case Center。
- 不做 Evaluation Center。
- 不做真实数据库 migration。
- 不做权限系统。
- 不做实时流。
- 不做真实世界速度标定。
- 不做执法级判断。
- 不做模型训练。
- 不做生产部署。

Stage 6 的设计重点是结果管理和读取契约，不把 Stage 5 已有事件规则能力包装成 Stage 6 完成态。

## 3. 当前基础审计

### 3.1 已有能力

当前已有以下能力：

- `backend/app/analysis/artifact_writer.py` 已有 `TrafficArtifactWriter`。
- `TrafficArtifactWriter.create_run_directory()` 会创建 run 目录和空 `keyframes/` 目录，并写入 `metadata.json`。
- `TrafficArtifactWriter.write_detection_outputs()` 会写入 `detections.csv`、`detections.jsonl`、`detection_summary.json`。
- `TrafficArtifactWriter.write_tracking_outputs()` 会写入 `tracks.csv`、`tracks.jsonl`、`tracking_summary.json`。
- `TrafficArtifactWriter.write_trajectory_outputs()` 会写入 `trajectory_points.csv`、`trajectory_points.jsonl`、`trajectory_summary.json`。
- `TrafficArtifactWriter.write_event_outputs()` 会写入 `events.jsonl`、`event_evidence.jsonl`、`rule_executions.jsonl`、`event_summary.json`。
- `TrafficArtifactWriter.write_alert_outputs()` 会写入 `alerts.jsonl`、`alert_summary.json`。
- `backend/app/services/traffic_analysis_service.py` 已有 in-memory run registry，并可从 `metadata.json` 回读 run。
- `TrafficAnalysisService` 已支持读取 detections、tracks、trajectory points、events、alerts。
- Stage 6B 已新增 `manifest.json`、`artifact_index.json`、metadata `artifact_summary` / `manifest_path` / `artifact_index_path`。
- Stage 6B 已新增 `GET /api/analysis-runs/{run_id}/manifest`。
- Stage 6C 已新增 `flow_counts.json`、`zone_statistics.json` 生成与读取。
- Stage 6C 已新增 `GET /api/analysis-runs/{run_id}/flow-counts` 和 `GET /api/analysis-runs/{run_id}/zone-statistics`。
- `backend/app/api/analysis_runs.py` 已有 `GET /api/analysis-runs`、`GET /api/analysis-runs/{run_id}`、manifest、detections、tracks、trajectory-points、events、flow-counts、zone-statistics、alerts 查询 API。
- `frontend/src/api/analysisRuns.ts` 已有 detections / tracks / trajectory / events / alerts API client；flow / zone statistics 前端接入留到 Stage 6E。
- `frontend/src/pages/AnalysisDetailPage.tsx` 已能读取并显示 detections、tracks、trajectory、events、alerts 的基础数据。

当前已真实生成和读取的产物如下：

| 产物 | 当前是否生成 | 生成模块 | 测试覆盖 | API 读取 | 前端读取 | 后续阶段 |
| --- | --- | --- | --- | --- | --- | --- |
| `metadata.json` | 是 | `TrafficArtifactWriter` 与各 service | tracking、trajectory、event、alert 相关测试 | `GET /api/analysis-runs/{run_id}` 间接读取 | Analysis Detail 通过 run summary 间接使用 | Stage 6B 加固 |
| `detections.csv` | 是 | `write_detection_outputs()` | tracking / trajectory service 测试 | `/detections` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `detections.jsonl` | 是 | `write_detection_outputs()` | tracking / trajectory service 测试 | `/detections` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `tracks.csv` | 是 | `write_tracking_outputs()` | tracking / trajectory service 测试 | `/tracks` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `tracks.jsonl` | 是 | `write_tracking_outputs()` | tracking / trajectory service 测试 | `/tracks` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `trajectory_points.csv` | 是 | `write_trajectory_outputs()` | trajectory service 测试 | `/trajectory-points` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `trajectory_points.jsonl` | 是 | `write_trajectory_outputs()` | trajectory / event service 测试 | `/trajectory-points` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `events.jsonl` | 是 | `write_event_outputs()` | event / stage5 pipeline 测试 | `/events` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `event_evidence.jsonl` | 是 | `write_event_outputs()` | event / stage5 pipeline 测试 | `/events` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `rule_executions.jsonl` | 是 | `write_event_outputs()` | event / rule execution 测试 | `/events` | Analysis Detail | 已有，Stage 6B 统一 manifest |
| `flow_counts.json` | 是 | `write_statistics_outputs()` | Stage 6C statistics 测试 | `/flow-counts` | 未接入图表 | Stage 6C |
| `zone_statistics.json` | 是 | `write_statistics_outputs()` | Stage 6C statistics 测试 | `/zone-statistics` | 未接入图表 | Stage 6C |
| `alerts.jsonl` | 是 | `write_alert_outputs()` | alert / stage5 pipeline 测试 | `/alerts` | Analysis Detail | 已有，Stage 6B 统一 manifest |

### 3.2 部分能力

当前已有 Stage 6B manifest / artifact index 与 Stage 6C traffic statistics 的 artifact-backed MVP。

- `TrafficArtifactWriter.CORE_ARTIFACTS` 包含 detections、tracks、trajectory、events、alerts、`flow_counts.json`、`zone_statistics.json`、`evaluation_summary.json`、`annotated_video.mp4`、`keyframes/` 等候选产物名。
- `TrafficArtifactWriter.artifact_index(run_id)` 只返回实际存在的文件或非空目录，因此候选产物不等于真实生成产物。
- `manifest.json` 使用 `schema_version=stage6b.v1`，按 artifact key 标注 `available`、`missing`、`planned`、`empty`、`error`。
- `artifact_index.json` 提供标准 artifact key 到相对路径的快速索引。
- `metadata.json` 保留原有字段，并补充 `schema_version`、`status`、`result_dir`、`manifest_path`、`artifact_index_path`、`artifact_summary`。
- `backend/app/analysis/run_index.py` 目前只有 `run_directory()` helper，不是 DB-backed result index，也不是完整运行索引服务。
- `backend/app/models/`、`backend/app/repositories/`、`backend/app/db/` 仍是 placeholder 或基础骨架。
- `keyframes/` 目录会被创建，但当前没有 snapshot 生成逻辑；空目录不会出现在 `artifact_index()`。
- 前端 Analysis Detail 已经存在，但更像 artifact reader 页面，还没有完整 Traffic Analysis Center 的 run 详情、artifact panel、flow/zone 统计图表。

### 3.3 未实现能力

当前未实现：

- `evaluation_summary.json` 生成。
- `annotated_video.mp4` final pipeline。
- keyframe snapshot 生成。
- `traffic_analysis_runs` 数据库表或 ORM model。
- DB-backed result index。
- flow / zone statistics 前端图表。
- Dashboard 真实 run 指标读取。
- Review Center、Bad Case Center、Evaluation Center。

### 3.4 当前风险

- `metadata.json` 中的旧 `artifacts` 字段仍保留兼容，不应替代 Stage 6B `manifest.json` 作为产物状态来源。
- `CORE_ARTIFACTS` 预留了尚未生成的产物名，若调用方直接读取 `metadata["artifacts"]` 而不校验文件存在，可能误判 Stage 6 产物已完成。
- `list_runs()` 当前只返回进程内 registry，不会扫描历史 run 目录；服务重启后只有按 `run_id` 查询时才会回读 metadata。
- `keyframes/` 目录虽然被创建，但没有 snapshot 生成和事件关联契约，不能视为 keyframe 能力完成。
- Stage 5 的 `flow_counting` 和 `congestion` 是规则层能力；Stage 6C 只消费它们的 artifacts 生成本地统计文件，不应被表述为数据库统计中心或前端统计图表完成。
- 真实数据库层还未建立，不能把当前 artifact-based / in-memory MVP 表述为 database final version。

## 4. Stage 6 总体设计

### 4.1 Traffic Analysis Center 的职责

Traffic Analysis Center 负责管理一次分析运行的结果，不负责重新定义检测、跟踪、轨迹和事件规则算法。

职责包括：

- 为每次分析生成稳定 `run_id`。
- 标准化结果目录和产物命名。
- 写入和维护 `metadata.json` 与 `manifest.json`。
- 提供按 `run_id` 查询的后端 API。
- 支持前端按 run 浏览结果、产物状态、摘要指标和明细数据。
- 为 Review Center、Bad Case Center、Evaluation Center 提供统一引用入口。

### 4.2 与 Stage 5 Event Engine 的边界

Stage 5 Event Engine 负责从 trajectory points 和规则配置生成：

- `events.jsonl`
- `event_evidence.jsonl`
- `rule_executions.jsonl`
- `alerts.jsonl`
- alert status transitions

Stage 6 不重新实现 Stage 5 的规则判断。Stage 6 只消费 Stage 5 产物，并把事件、证据、告警纳入统一 run result contract。

### 4.3 与 Stage 7 Review Center 的边界

Stage 7 Review Center 负责人工复核、事件确认、误报标注和 review comments。Stage 6 只提供 event、alert、evidence、keyframe、video artifact 的稳定读取入口，不保存 review decision。

Stage 6 manifest 可以预留 `review_status` 或 `review_artifacts` 的扩展位置，但不实现复核流程。

### 4.4 与 Stage 8 Evaluation Center 的边界

Stage 8 Evaluation Center 负责评估指标、ground truth 对比、模型或规则质量报告。Stage 6 只保留 `evaluation_summary.json` 的设计位置，不生成 evaluation result，不计算 precision / recall / false positive rate。

## 5. Run 结果目录设计

### 5.1 推荐目录结构

推荐 Stage 6 完整目录如下：

```text
results/traffic_analysis/<run_id>/
  metadata.json
  manifest.json
  artifact_index.json
  detections.csv
  detections.jsonl
  detection_summary.json
  tracks.csv
  tracks.jsonl
  tracking_summary.json
  trajectory_points.csv
  trajectory_points.jsonl
  trajectory_summary.json
  events.jsonl
  event_evidence.jsonl
  rule_executions.jsonl
  event_summary.json
  alerts.jsonl
  alert_summary.json
  flow_counts.json
  zone_statistics.json
  keyframes/
    event_<event_id>.jpg
  annotated_video.mp4
```

### 5.2 必需产物

Stage 6B 的最小必需产物建议为：

- `metadata.json`
- `manifest.json`
- `artifact_index.json`
- 已存在时纳入 manifest 的 detections / tracks / trajectory / events / alerts 产物

Stage 6C 的必需产物建议为：

- `flow_counts.json`
- `zone_statistics.json`

### 5.3 可选产物

可选产物包括：

- `detection_preview.mp4`
- `tracking_preview.mp4`
- `annotated_video.mp4`
- `keyframes/`
- `evaluation_summary.json`

可选产物必须在 manifest 中标记为 `missing`、`skipped` 或 `not_applicable`，不能通过缺文件让调用方自行猜测状态。

### 5.4 暂不实现产物

Stage 6A 不实现任何产物。后续 Stage 6B/6C/6F 仍应暂不实现：

- Review artifacts。
- Bad Case artifacts。
- Evaluation detail artifacts。
- 数据库表迁移产物。

## 6. Artifact Manifest 设计

### 6.1 manifest.json 目标

`manifest.json` 是面向 API 和前端的稳定产物目录。它应解决三个问题：

- 该 run 理论上有哪些产物。
- 每个产物当前是否存在、是否可读、是否可下载。
- 每个产物来自哪个 pipeline stage，是否有错误或跳过原因。

### 6.2 字段设计

建议结构：

```json
{
  "run_id": "run_abc123",
  "video_id": "video_001",
  "schema_version": "stage6.manifest.v1",
  "created_at": "2026-06-24T00:00:00Z",
  "updated_at": "2026-06-24T00:00:00Z",
  "pipeline_stage": "stage_5_alert_center_mvp",
  "artifacts": [
    {
      "key": "detections_csv",
      "path": "detections.csv",
      "type": "csv",
      "stage": "stage_2_detection",
      "status": "available",
      "required": true,
      "size_bytes": 1234,
      "record_count": 100,
      "created_at": "2026-06-24T00:00:00Z",
      "error": null
    }
  ],
  "summary": {
    "total_frames_processed": 100,
    "total_detections": 200,
    "total_tracks": 30,
    "total_events": 5,
    "total_alerts": 3
  }
}
```

### 6.3 artifact 状态枚举

建议状态：

- `available`: 文件或非空目录存在，并可读取。
- `missing`: 该阶段理论要求存在，但当前缺失。
- `reserved`: 设计预留，当前阶段不生成。
- `skipped`: 因配置或运行条件主动跳过。
- `failed`: 产物生成失败，有错误原因。
- `not_applicable`: 对该 run 不适用，例如 detection-only run 不要求 trajectory。

### 6.4 与 metadata.json 的关系

`metadata.json` 负责描述 run 本身，包括输入视频、pipeline 配置、阶段状态、统计摘要和 config snapshot。

`manifest.json` 负责描述 artifacts，包括路径、状态、类型、大小、记录数、是否 required、错误信息。

两者都可以保留 `run_id` 和 `video_id`，但不应让调用方从 `metadata["artifacts"]` 推断完整产物状态。Stage 6B 可以先让 `metadata.json` 引用 `manifest.json`，再逐步收敛旧的 `artifacts` 字段。

## 7. metadata.json 设计

### 7.1 当前 metadata 能力

当前 `metadata.json` 已能记录：

- `run_id`
- `video_id`
- `created_at`
- `stage`
- `next_stage`
- `artifacts`
- detector / tracker / trajectory 配置片段
- event config snapshot
- events、evidence、rule executions、alerts 计数

### 7.2 Stage 6 需要补充的字段

建议补充：

- `schema_version`
- `status`
- `started_at`
- `completed_at`
- `duration_ms`
- `input_video`
- `video_metadata`
- `pipeline_mode`
- `pipeline_stages`
- `config_snapshot`
- `manifest_path`
- `artifact_index_path`
- `summary`
- `errors`
- `warnings`

### 7.3 run_id / video_id / config snapshot 关系

- `run_id` 表示一次分析运行，是结果目录和 API 查询的主键。
- `video_id` 表示输入视频，可被多个 run 复用。
- `config_snapshot` 记录本次运行实际使用的 detector、tracker、trajectory、event rules、zones、alert config。
- 后续数据库实现时，`traffic_analysis_runs` 应以 `run_id` 为主键或唯一键，并保留 `video_id` 外键或引用字段。

## 8. flow_counts.json 设计

### 8.1 与 Stage 5 flow_counting event 的区别

`flow_counting` 是 Stage 5 Event Engine 的事件规则。它关注单条 track segment 是否穿越 `rule.parameters.line`，并生成 event / evidence。它支持 `direction=any / positive / negative` 和 `count_once_per_track`。

`flow_counts.json` 是 Stage 6 的聚合统计产物。它关注按 line、zone、class、direction、time window 汇总计数。

Stage 6C 已基于 Stage 5 的 `flow_counting` event / evidence 生成 artifact-backed `flow_counts.json`。这仍只是本地 artifact MVP，不等同于数据库统计中心、前端流量图表或真实世界流量标定完成。

### 8.2 数据结构

当前 Stage 6C 结构：

```json
{
  "schema_version": "stage6.flow_counts.v1",
  "run_id": "run_abc123",
  "video_id": "video_001",
  "window_ms": 60000,
  "source_artifacts": {
    "events": "events.jsonl",
    "event_evidence": "event_evidence.jsonl",
    "rule_executions": "rule_executions.jsonl"
  },
  "windows": [
    {
      "time_window_start_ms": 0,
      "time_window_end_ms": 60000,
      "zone_id": "zone_entry",
      "counting_line_id": "line_northbound",
      "class_name": "car",
      "direction": "in",
      "in_count": 12,
      "out_count": 0,
      "unknown_direction_count": 0,
      "total_count": 12,
      "track_ids": [1, 2, 3],
      "event_ids": ["event_1"]
    }
  ],
  "records": [],
  "summary": {
    "total_count": 12,
    "vehicle_count": 12,
    "person_count": 0,
    "by_class": {"car": 12},
    "by_zone": {"zone_entry": 12},
    "by_line": {"line_northbound": 12},
    "by_direction": {"in": 12}
  }
}
```

### 8.3 生成时机

Stage 6C 已生成，输入使用：

- `events.jsonl` 中的 `flow_counting` event。
- `event_evidence.jsonl` 中 `evidence_type=line_crossing` 的 evidence。
- `rule_executions.jsonl` 作为 source artifact 引用。

### 8.4 API 读取方式

已新增：

- `GET /api/analysis-runs/{run_id}/flow-counts`

当前 API 返回完整 artifact payload，尚未实现 query filter。

### 8.5 当前不做的内容

当前不做：

- 真实世界速度或车流标定。
- 跨摄像头去重。
- 长周期数据库聚合。
- 前端高级统计图表。
- 执法级流量结论。

## 9. zone_statistics.json 设计

### 9.1 与 Stage 5 congestion evidence 的区别

`congestion` 是 Stage 5 aggregate event rule。它可以基于区域内车辆数量和平均像素速度生成 `congestion` event，其 evidence 中可能包含 `evidence_type=zone_statistics`。

`zone_statistics.json` 是 Stage 6 的区域统计产物。它应保存 frame / window 级别的 `vehicle_count`、`person_count`、`avg_speed`、`occupancy` 等统计。

Stage 6C 已基于 explicit trajectory zone data 和 congestion evidence 生成 artifact-backed `zone_statistics.json`。这仍只是本地 artifact MVP，不等同于数据库区域统计中心、前端拥堵图表或真实世界拥堵标定完成。

### 9.2 数据结构

当前 Stage 6C 结构：

```json
{
  "schema_version": "stage6.zone_statistics.v1",
  "run_id": "run_abc123",
  "video_id": "video_001",
  "window_ms": 60000,
  "source_artifacts": {
    "trajectory_points": "trajectory_points.jsonl",
    "events": "events.jsonl",
    "event_evidence": "event_evidence.jsonl"
  },
  "windows": [
    {
      "zone_id": "intersection_core",
      "time_window_start_ms": 0,
      "time_window_end_ms": 60000,
      "vehicle_count": 8,
      "person_count": 2,
      "occupancy_count": 10,
      "avg_speed_px_per_frame": 1.25,
      "class_counts": {"car": 8, "person": 2},
      "track_ids": [1, 2, 3]
    }
  ],
  "congestion_events": [],
  "summary": {
    "max_vehicle_count": 8,
    "zone_count": 1,
    "total_windows": 1,
    "congestion_event_count": 0
  }
}
```

### 9.3 生成时机

Stage 6C 已生成，输入使用：

- `trajectory_points.jsonl` 中已有的 `zone_ids` / `zone_id` / `zone_history`。
- `events.jsonl` 中的 `congestion` event。
- `event_evidence.jsonl` 中 `evidence_type=zone_statistics` 的 evidence。

### 9.4 API 读取方式

已新增：

- `GET /api/analysis-runs/{run_id}/zone-statistics`

当前 API 返回完整 artifact payload，尚未实现 query filter。

### 9.5 当前不做的内容

当前不做：

- 基于真实物理面积的占有率标定。
- 交通信号灯相位关联。
- 拥堵等级执法判断。
- 长期趋势数据库分析。

## 10. keyframes 设计

### 10.1 keyframe 用途

keyframe 用于给事件、告警、复核和评估提供静态视觉证据。它应服务于“快速查看事件发生时刻”，不是替代 annotated video。

### 10.2 命名规则

建议命名：

```text
keyframes/event_<event_id>.jpg
keyframes/alert_<alert_id>.jpg
keyframes/frame_<frame_index>.jpg
```

文件名应只包含安全字符，不应直接拼接用户输入。

### 10.3 与 events / alerts / evidence 的关联

建议在 `event_evidence.jsonl` 中保留：

- `snapshot_path`
- `snapshot_available`
- `frame_index`
- `timestamp_ms`
- `bbox`
- `track_id`

alerts 可以引用 event evidence，而不是重复保存 snapshot 信息。

### 10.4 当前阶段是否实现

当前没有实现 keyframe snapshot 生成。`keyframes/` 目录会被创建，但空目录不代表能力完成。Stage 6A 只设计，Stage 6F 再实现。

## 11. annotated_video 设计

### 11.1 用途

`annotated_video.mp4` 用于离线回看检测框、track id、轨迹线、事件标记和告警标记。

### 11.2 输入

建议输入：

- 原始视频文件。
- `detections.jsonl`
- `tracks.jsonl`
- `trajectory_points.jsonl`
- `events.jsonl`
- `alerts.jsonl`
- zone / line config snapshot。

### 11.3 输出

输出：

- `annotated_video.mp4`
- manifest 中对应 artifact 记录。
- 可选的 overlay summary，例如绘制耗时、帧数、跳过原因。

### 11.4 与检测/跟踪/事件 overlay 的关系

前端 overlay 是交互式查看，`annotated_video.mp4` 是离线渲染结果。两者应共享同一组 artifact 和配置语义，但不要求使用相同渲染实现。

### 11.5 当前阶段是否实现

当前没有 final annotated_video pipeline。现有 preview video 仅属于 detection / tracking 阶段可选预览，不是 Stage 6 的完整 annotated video。

## 12. API Contract 草案

### 12.1 Analysis Run Summary

已有：

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`

建议稳定字段：

```json
{
  "id": "run_abc123",
  "video_id": "video_001",
  "status": "completed",
  "result_dir": "results/traffic_analysis/run_abc123",
  "stage": "stage_5_alert_center_mvp",
  "summary": {
    "total_frames_processed": 100,
    "total_detections": 200,
    "total_tracks": 30,
    "total_events": 5,
    "total_alerts": 3
  },
  "artifact_index": {
    "metadata": "metadata.json",
    "manifest": "manifest.json"
  }
}
```

当前 `list_runs()` 只返回 in-memory registry。Stage 6B 应考虑扫描已有 run 目录或建立持久索引。

### 12.2 Artifact Manifest API

建议新增：

- `GET /api/analysis-runs/{run_id}/manifest`

返回 `manifest.json` 的公开字段。该 API 是前端 Artifact Panel 的主要数据源。

### 12.3 Detections API

已有：

- `GET /api/analysis-runs/{run_id}/detections`

当前数据来源：

- `detection_summary.json`
- `detections.jsonl`
- `detections.csv`

Stage 6B 建议保留现有响应，同时补充 schema version 和 artifact source 信息。

### 12.4 Tracks API

已有：

- `GET /api/analysis-runs/{run_id}/tracks`

当前数据来源：

- `tracking_summary.json`
- `tracks.jsonl`
- `tracks.csv`

Stage 6B 建议保留 limit 参数，并统一错误响应。

### 12.5 Trajectory Points API

已有：

- `GET /api/analysis-runs/{run_id}/trajectory-points`

当前数据来源：

- `trajectory_summary.json`
- `trajectory_points.jsonl`
- `trajectory_points.csv`

已支持：

- `limit`
- `track_id`

### 12.6 Events API

已有：

- `GET /api/analysis-runs/{run_id}/events`

当前数据来源：

- `event_summary.json`
- `events.jsonl`
- `event_evidence.jsonl`
- `rule_executions.jsonl`

已支持：

- `limit`
- `event_type`
- `track_id`

### 12.7 Alerts API

已有：

- `GET /api/analysis-runs/{run_id}/alerts`
- `POST /api/analysis-runs/{run_id}/alerts/generate`

当前数据来源：

- `alert_summary.json`
- `alerts.jsonl`

Alert Center API 另已支持 query、acknowledge、resolve、ignore。Stage 6 只需要把 alert artifacts 纳入统一 run contract。

### 12.8 Flow Counts API

当前 Stage 6C 已实现 artifact-backed 读取。

已新增：

- `GET /api/analysis-runs/{run_id}/flow-counts`

数据来源：

- `flow_counts.json`

如果 run 存在但文件缺失，service 会基于现有 event / evidence artifacts 生成该文件；没有 `flow_counting` 记录时返回合法空统计。缺失 run 返回 404。

### 12.9 Zone Statistics API

当前 Stage 6C 已实现 artifact-backed 读取。

已新增：

- `GET /api/analysis-runs/{run_id}/zone-statistics`

数据来源：

- `zone_statistics.json`

如果 run 存在但文件缺失，service 会基于现有 trajectory / event / evidence artifacts 生成该文件；没有 zone 数据时返回合法空统计。缺失 run 返回 404。

## 13. 前端页面草案

### 13.1 Dashboard

当前 Dashboard 主要是静态指标。Stage 6E 建议接入：

- 最近 runs。
- 总 detections / tracks / events / alerts。
- alert status 分布。
- flow counts 摘要。
- zone statistics 摘要。

### 13.2 Video Center

Video Center 当前可以上传和发起处理，并展示部分处理结果。Stage 6E 建议增加：

- 每个视频关联的 recent runs。
- 进入 Analysis Detail 的入口。
- run 状态和主要产物状态。

### 13.3 Analysis Detail

当前 Analysis Detail 已读取 detections、tracks、trajectory、events、alerts。Stage 6E 建议增强：

- run summary header。
- artifact manifest panel。
- flow counts panel。
- zone statistics panel。
- keyframes panel 占位状态。
- annotated video 占位状态。

### 13.4 Artifact Panel

Artifact Panel 读取 manifest，展示：

- artifact key。
- type。
- status。
- required / optional。
- size。
- record count。
- source stage。
- error 或 skipped reason。

### 13.5 Flow / Zone Statistics Panel

Flow / Zone Statistics Panel 读取：

- `/flow-counts`
- `/zone-statistics`

初始版本可只展示表格和小型摘要，不需要复杂图表。缺失时应显示“未生成”，不能显示 0 误导用户。

## 14. 测试策略

### 14.1 ArtifactWriter 测试

覆盖：

- `metadata.json` 写入和更新。
- `manifest.json` 写入。
- `artifact_index.json` 写入。
- 已存在产物的 `available` 状态。
- 未生成但预留产物的 `reserved` 或 `missing` 状态。
- 空 `keyframes/` 不应被误判为 available。

### 14.2 Manifest 测试

覆盖：

- manifest schema version。
- required artifact 缺失时状态正确。
- optional artifact 缺失时状态正确。
- 文件大小、记录数、类型字段正确。
- 相对路径校验，禁止绝对路径和目录穿越。

### 14.3 API 测试

覆盖：

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/manifest`
- detections / tracks / trajectory / events / alerts 回归。
- `/flow-counts` 和 `/zone-statistics` 缺失 run 时清晰 404。
- flow / zone 产物存在时正常返回。
- run 存在但统计产物缺失时可生成合法空或非空 artifact。

### 14.4 前端 build 测试

覆盖：

- `npm run build`。
- Analysis Detail 在缺失 flow / zone / keyframes / annotated_video 时不崩溃。
- Artifact Panel 正确显示 missing / reserved / available。

### 14.5 回归测试

保留并运行现有：

- Stage 2 detection tests。
- Stage 3 tracking tests。
- Stage 4 trajectory tests。
- Stage 5 event / alert tests。
- Alert status transition tests。

Stage 6 不应破坏已有 artifact 格式。

## 15. Stage 6 子阶段拆分

### 15.1 Stage 6B：Run manifest 与 artifact index 加固

已实现范围：

- 新增 manifest builder。
- 生成 `manifest.json`。
- 生成 `artifact_index.json`。
- 加固 `metadata.json`，补充 artifact summary 和 manifest/index 相对路径。
- 新增 `/api/analysis-runs/{run_id}/manifest`。
- 为 manifest/index builder 和 API 增加后端测试。
- 不改检测、跟踪、轨迹、事件、告警算法。

### 15.2 Stage 6C：flow_counts.json 与 zone_statistics.json

已实现范围：

- 基于 `flow_counting` events 和 line-crossing evidence 生成 `flow_counts.json`。
- 基于 explicit trajectory zone data 和 congestion evidence 生成 `zone_statistics.json`。
- 新增读取 service 和 API。
- 只做像素坐标统计，不做真实世界标定。

### 15.3 Stage 6D：Analysis Runs API 增强

最小范围：

- 统一 run summary schema。
- 支持服务重启后扫描 run 目录。
- 统一错误响应。
- 增加 artifact source 和 schema version。

### 15.4 Stage 6E：前端 Analysis Detail / Dashboard 真实数据接入

最小范围：

- Artifact Panel。
- Dashboard 读取真实 run summary。
- Flow / Zone Statistics Panel 基础表格。
- 缺失产物状态展示。

### 15.5 Stage 6F：keyframes 与 annotated_video pipeline

最小范围：

- 基于 event / alert 生成 keyframe snapshot。
- manifest 标记 keyframes 状态。
- 设计并实现离线 annotated video pipeline。
- 不做人工复核和评估。

### 15.6 Stage 6G：文档、测试、tag 收尾

最小范围：

- 更新 README 和 API docs。
- 补齐测试。
- 跑完整检查。
- 在用户明确要求后再 commit、push、tag。

## 16. 风险与规避

| 风险 | 影响 | 规避 |
| --- | --- | --- |
| 把 `CORE_ARTIFACTS` 预留键当成真实产物 | 前端误判 Stage 6 完成 | 使用 manifest status，必须校验文件存在 |
| in-memory registry 丢失历史 run | 服务重启后列表为空 | Stage 6D 扫描 run 目录或引入持久索引 |
| flow_counting event 与 flow_counts 混淆 | 统计中心能力被夸大 | 文档、API、命名上明确 event vs aggregate artifact |
| congestion evidence 与 zone statistics 混淆 | 区域统计能力被夸大 | `zone_statistics.json` 独立生成和读取 |
| metadata 字段继续扩散 | 前端和后续模块难以依赖 | Stage 6B 固定 schema version |
| 一次性引入数据库 | 范围过大，破坏 MVP | Stage 6 先保持 artifact-based，数据库留到后续明确阶段 |
| keyframes / annotated video 过早实现 | 容易牵动视频渲染和存储细节 | Stage 6F 单独小步实现 |

## 17. Stage 6B / 6C 完成状态与后续边界

Stage 6B 已完成 run manifest 与 artifact index 加固：

1. 新增 `stage6b.v1` manifest schema 和 builder。
2. 为 run 目录生成 `manifest.json` 和 `artifact_index.json`。
3. 在 `metadata.json` 中加入 `schema_version`、`status`、`result_dir`、`manifest_path`、`artifact_index_path`、`artifact_summary`。
4. 新增 `GET /api/analysis-runs/{run_id}/manifest`。
5. 为 manifest builder、artifact index、metadata summary 和 manifest API 增加后端测试。

Stage 6B 没有实现 `flow_counts.json`、`zone_statistics.json`、keyframes、annotated video、Review、Bad Case、Evaluation 或数据库 migration。

Stage 6C 已完成 artifact-backed traffic statistics MVP：

1. 新增 `flow_counts.json` 和 `zone_statistics.json` 生成。
2. 将 Stage 6C artifacts 纳入 manifest / artifact index / metadata summary。
3. 新增 `GET /api/analysis-runs/{run_id}/flow-counts`。
4. 新增 `GET /api/analysis-runs/{run_id}/zone-statistics`。
5. 为 writer、manifest 状态和 API 增加后端测试。

Stage 6C 没有实现 keyframes、annotated video、Review、Bad Case、Evaluation、数据库 migration、DB-backed result index、前端统计图表或真实世界速度 / 流量标定。下一步建议进入 Stage 6D：Analysis Runs API 增强和历史 run 目录扫描。
