# SmartTraffic Demo / Sample 计划

本文档记录当前 final local delivery 的 demo / sample 收口结果。本仓库只提供小型配置和 toy expected annotation，不提交视频、模型权重或 generated results。

## 1. 当前状态

- `samples/videos/` 存在，仅保留 `.gitkeep`。
- `samples/configs/` 已提供小型 zone、event rule 和 processing request 示例。
- `evals/expected/` 已提供 toy expected events / counts 示例。
- `evals/datasets/`、`evals/results/` 和 `evals/scripts/` 继续只保留 `.gitkeep` 或后续小型文本配置。
- `scripts/seed_demo_data.py` 是当前 demo seed MVP，可生成小型 demo/sample 配置和 toy expected annotation。
- `scripts/run_evals.py` 是 Stage 8HI artifact-backed Evaluation runner CLI，可对已有本地 run artifacts 执行 MVP evaluation。

## 2. Demo 数据原则

- 不提交大视频。
- 不提交模型权重。
- 不提交真实生成结果。
- 不下载公开数据集到仓库。
- 用户可在本地放置视频到 `local_videos/`，模型权重到 `local_models/`。
- 演示优先使用 dry-run detection / tracking，确保无权重环境也能跑通基础链路。
- 如需公开视频，只在文档中说明来源和下载方式，不把视频文件纳入 Git。

## 3. Sample Config

当前 demo seed 已补充以下小型文本配置：

- `samples/configs/demo_zones.json`：1 个 vehicle lane、1 个 danger zone、1 个 no-parking zone、1 个 counting line。
- `samples/configs/demo_event_rules.json`：wrong-way、danger-zone intrusion、illegal-parking、pedestrian-lane intrusion、congestion、flow-counting 六条 toy event rules。
- `samples/configs/demo_processing_request.json`：可用于 `POST /api/videos/{video_id}/process` 的 dry-run request body 示例。
- `evals/expected/demo_expected_events.json`：6 条 toy expected event。
- `evals/expected/demo_expected_counts.json`：2 条 toy flow count。

这些文件必须保持小型、可审计、可手工阅读，不包含真实视频帧、模型输出大文件或隐私数据。

## 4. Demo Seed

生成或补齐默认 demo/sample 文件：

```bash
python3 scripts/seed_demo_data.py
```

只打印计划写入的文件：

```bash
python3 scripts/seed_demo_data.py --dry-run
```

覆盖已有文件：

```bash
python3 scripts/seed_demo_data.py --force
```

写入临时目录：

```bash
python3 scripts/seed_demo_data.py --output-root /tmp/smarttraffic-demo-seed --force
```

`scripts/seed_demo_data.py` 只生成 toy config / expected records，用于说明目录结构和 API contract。它不应：

- 生成真实视频。
- 生成模型权重。
- 批量生成大量 run results。
- 覆盖用户已有 results。
- 自动创建 Bad Case 或 Evaluation 结论。

Demo seed 验收：

```bash
./backend/.venv/bin/python -m pytest backend/tests/test_seed_demo_data.py -q
```

## 5. Evaluation MVP Toy Input

`evals/expected/demo_expected_events.json` 可作为 Evaluation MVP 的 `expected_events_path` 输入，`evals/expected/demo_expected_counts.json` 可作为 `expected_counts_path` 输入。它们只用于 smoke/demo，不代表真实 benchmark，也不包含 industrial-grade mAP / IDF1 / MOTA 标注。

## 6. Local Delivery 验收

- 无模型权重时，可通过 dry-run 跑通 upload -> process -> artifacts -> frontend 展示。
- 有本地视频和权重时，可按 README 配置真实 YOLOv8 推理，但输出只保存在 ignored 本地目录。
- Docker Compose 可用于本地验证 / demo，启动 backend、frontend、SQLite 和本地目录挂载；它不是生产部署声明。
- demo 文档能说明如何清理本地 results。
- danger check、tracked forbidden scan 和大文件扫描均通过。

## 7. 不做事项

- 不实现生产 demo 平台。
- 不提交 public dataset copy。
- 不提交 generated evaluation results。
- 不把 demo seed 当成 Evaluation ground truth 管理系统。
- 不把 dry-run demo 结果写成真实性能指标。
