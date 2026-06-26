# SmartTraffic Demo / Sample 计划

本文档记录 Stage 9CD 前的 demo / sample 计划。Stage 9AB 不实现大 demo 数据，也不提交视频、模型权重或 generated results。

## 1. 当前状态

- `samples/videos/` 存在，仅保留 `.gitkeep`。
- `evals/datasets/`、`evals/expected/`、`evals/results/` 和 `evals/scripts/` 存在，仅保留 `.gitkeep` 或后续小型文本配置。
- `scripts/seed_demo_data.py` 是 Stage 9 planned demo seed placeholder，不生成真实 demo 数据，不实现 Bad Case 或 Evaluation 功能。
- `scripts/run_evals.py` 是 Stage 8HI artifact-backed Evaluation runner CLI，可对已有本地 run artifacts 执行 MVP evaluation。

## 2. Demo 数据原则

- 不提交大视频。
- 不提交模型权重。
- 不提交真实生成结果。
- 不下载公开数据集到仓库。
- 用户可在本地放置视频到 `local_videos/`，模型权重到 `local_models/`。
- 演示优先使用 dry-run detection / tracking，确保无权重环境也能跑通基础链路。
- 如需公开视频，只在文档中说明来源和下载方式，不把视频文件纳入 Git。

## 3. Sample Config 计划

Stage 9CD 可以补充小型文本配置：

- sample zone polygon。
- sample event rules。
- sample evaluation dataset registry。
- sample expected event / flow count JSON。
- dry-run demo command sequence。

这些文件必须保持小型、可审计、可手工阅读，不包含真实视频帧、模型输出大文件或隐私数据。

## 4. Demo Seed 计划

`scripts/seed_demo_data.py` 后续只应生成 toy metadata / config / expected records，用于说明目录结构和 API contract。它不应：

- 生成真实视频。
- 生成模型权重。
- 批量生成大量 run results。
- 覆盖用户已有 results。
- 自动创建 Bad Case 或 Evaluation 结论。

## 5. Stage 9CD 建议验收

- 无模型权重时，可通过 dry-run 跑通 upload -> process -> artifacts -> frontend 展示。
- 有本地视频和权重时，可按 README 配置真实 YOLOv8 推理，但输出只保存在 ignored 本地目录。
- demo 文档能说明如何清理本地 results。
- danger check、tracked forbidden scan 和大文件扫描均通过。

## 6. 不做事项

- 不实现生产 demo 平台。
- 不提交 public dataset copy。
- 不提交 generated evaluation results。
- 不把 demo seed 当成 Evaluation ground truth 管理系统。
- 不把 dry-run demo 结果写成真实性能指标。
