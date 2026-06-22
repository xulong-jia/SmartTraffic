# Stage 4 Trajectory Engine

## 1. 阶段目标

Stage 4 的目标是把阶段三产生的 tracks 转换为可查询、可保存、可解释的 `trajectory_points`，为后续 Event Engine 提供 speed、direction、track_length、dwell_time、zone 预留字段等输入。

本阶段只完成轨迹特征生成、产物保存、API 查询和前端最小展示，不包含交通事件判断。

## 2. 当前完成内容

- Geometry 工具
- Trajectory Features
- TrajectoryEngine
- Trajectory artifacts
- Trajectory Service
- API
- Frontend minimal view
- Tests

## 3. 模块结构

- `backend/app/trajectory/geometry.py`
- `backend/app/trajectory/features.py`
- `backend/app/trajectory/engine.py`
- `backend/app/services/trajectory_service.py`
- `backend/app/analysis/artifact_writer.py`
- `backend/app/api/analysis_runs.py`
- `frontend/src/pages/VideoCenterPage.tsx`
- `frontend/src/pages/AnalysisDetailPage.tsx`

## 4. Geometry 工具

阶段四已实现以下几何工具：

- `point_in_polygon`
- `bbox_center`
- `bbox_bottom_center`
- `segment_intersects_line`
- `line_crossing_direction`
- `vector_angle`
- `angle_difference`

这些函数为后续 zone relation、line crossing 和 direction rule 提供基础几何能力。

## 5. Trajectory Features

阶段四已实现以下轨迹特征工具：

- `compute_speed`
- `compute_direction_vector`
- `compute_moving_angle`
- `compute_track_length`
- `compute_dwell_time`

`speed_px_per_second` 是基于 timestamp 或 fps 计算的像素级速度估算，不是真实世界 m/s 或 km/h。

`dwell_time_ms` 只是基于低速或近似静止状态累计的时间特征，不是违停事件。

## 6. TrajectoryEngine contract

TrajectoryEngine 输入来自阶段三 tracking frame result。

输入 tracks contract：

```json
{
  "frame_index": 12,
  "timestamp_ms": 400,
  "tracks": [
    {
      "track_id": 1,
      "class_id": 2,
      "class_name": "car",
      "confidence": 0.91,
      "bbox": [10, 20, 50, 80],
      "center": [30, 50],
      "state": "confirmed"
    }
  ]
}
```

输出 trajectory_points contract：

```json
{
  "frame_index": 12,
  "timestamp_ms": 400,
  "trajectory_points": [
    {
      "track_id": 1,
      "class_id": 2,
      "class_name": "car",
      "confidence": 0.91,
      "bbox": [10, 20, 50, 80],
      "center": [30, 50],
      "bottom_center": [30, 80],
      "state": "confirmed",
      "speed_px_per_frame": 4.2,
      "speed_px_per_second": 42.0,
      "direction_vector": [4.0, 1.0],
      "moving_angle": 14.036,
      "dwell_time_ms": 0,
      "zone_ids": [],
      "zone_history": [],
      "lane_relation": {},
      "line_crossings": [],
      "track_length": 3,
      "last_seen_frame": 12,
      "last_seen_timestamp_ms": 400
    }
  ]
}
```

输出字段包括：

- `track_id`
- `class_id`
- `class_name`
- `confidence`
- `bbox`
- `center`
- `bottom_center`
- `state`
- `speed_px_per_frame`
- `speed_px_per_second`
- `direction_vector`
- `moving_angle`
- `dwell_time_ms`
- `zone_ids`
- `zone_history`
- `lane_relation`
- `line_crossings`
- `track_length`
- `last_seen_frame`
- `last_seen_timestamp_ms`

`zone_ids`、`zone_history`、`lane_relation` 当前是为后续 Zone Config / Event Engine 预留。当前不做交通事件判断。

## 7. Trajectory artifacts

阶段四处理后会生成：

```text
results/traffic_analysis/<run_id>/
  trajectory_points.csv
  trajectory_points.jsonl
  trajectory_summary.json
```

`trajectory_points.csv` 主要字段：

- `run_id`
- `video_id`
- `frame_index`
- `timestamp_ms`
- `track_id`
- `class_id`
- `class_name`
- `confidence`
- `state`
- `x1`
- `y1`
- `x2`
- `y2`
- `center_x`
- `center_y`
- `bottom_center_x`
- `bottom_center_y`
- `speed_px_per_frame`
- `speed_px_per_second`
- `direction_x`
- `direction_y`
- `moving_angle`
- `dwell_time_ms`
- `zone_ids_json`
- `zone_history_json`
- `lane_relation_json`
- `line_crossings_json`
- `track_length`
- `last_seen_frame`
- `last_seen_timestamp_ms`

`trajectory_summary.json` 主要字段：

- `run_id`
- `video_id`
- `total_frames_processed`
- `total_trajectory_points`
- `unique_track_ids`
- `per_class_track_counts`
- `track_state_counts`
- `avg_track_length`
- `max_track_length`
- `speed_unit`
- `avg_speed_px_per_second`
- `zone_counts`
- `line_crossing_counts`

## 8. API

`POST /api/videos/{video_id}/process`

支持 mode：

- `detection_tracking_trajectory`

新增参数：

- `direction_window`
- `dwell_speed_threshold`
- `max_history_points`

新增查询：

`GET /api/analysis-runs/{run_id}/trajectory-points`

支持：

- `limit`
- `track_id`

返回：

- `summary`
- `frames`
- `rows`

## 9. Frontend minimal view

阶段四前端最小展示包括：

- VideoCenter 支持 trajectory mode
- AnalysisDetail 支持 trajectory summary / rows / frames
- 支持 `track_id` filter

当前不做视频 overlay，不画轨迹线。

## 10. Tests and acceptance

阶段四测试覆盖：

- `test_trajectory_geometry.py`
- `test_trajectory_features.py`
- `test_trajectory_engine_contract.py`
- `test_artifact_writer.py`
- `test_trajectory_service.py`
- `test_trajectory_api.py`
- frontend `npm run build`

验收重点：

- Geometry 工具边界情况可测
- speed / direction / dwell / track_length 可计算
- TrajectoryEngine 能维护内存 track state cache
- trajectory artifacts 能写入 CSV / JSONL / summary
- API 能查询 trajectory points 并支持 `limit` / `track_id`
- 前端能最小展示 trajectory summary / rows / frames

## 11. Current boundaries

当前阶段四不包含：

- Event Engine
- 逆行、违停、闯入、行人入机动车道、拥堵事件判断
- Alert / Review / Bad Case / Evaluation
- 正式交通执法用途
- 真实世界速度标定

当前 `speed_px_per_second` 不代表真实世界 m/s 或 km/h。
