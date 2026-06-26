# Evaluation Center

本文档记录 Stage 8HI 后的 Evaluation Center artifact-backed MVP。它不是
数据库最终版，也不代表工业级检测 / 跟踪评测体系已经完成。

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

当前仍未实现：

- 真实 rerun-based Bad Case regression pipeline。
- 工业级 mAP、IDF1、MOTA。
- database-backed evaluation tables。
- 权限、多用户、实时流或生产部署。

## Artifacts

Evaluation artifacts 位于 `evals/`，真实 generated results 不应提交到 Git。
仓库只保留 `.gitkeep` 占位目录。

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

## API

Stage 8EFG 提供以下 artifact-backed endpoints：

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
`detection`、`tracking`、`regression` 类型。其中 `regression` 读取当前
run 的 `bad_cases.jsonl`，输出 artifact-backed regression summary MVP；
它不执行真实模型重跑。

## Metrics MVP

当前指标是 artifact-backed MVP：

- Event：按 `event_type` 和 frame range overlap / tolerance 做贪心匹配，
  输出 precision、recall、F1，并把 unmatched expected / actual 写为
  failed cases。
- Flow counting：比较 expected counts 与 `flow_counts.json` 的 total、
  class、direction 误差，输出 absolute error、MAE、MAPE。
- Trajectory：从 `trajectory_points.jsonl` 统计 track count、trajectory
  point count、average track length、average speed、direction availability。
- Detection：若没有检测标注，返回 `not_applicable`；不宣称 mAP 已实现。
- Tracking：若没有跟踪标注，返回 `not_applicable`；不宣称 IDF1 / MOTA 已实现。
- Regression：读取 Bad Case status，输出 `total_cases`、`open_cases`、
  `fixed_cases`、`verified_cases`、`ignored_cases`、`fixed_case_count`、
  `reopened_case_count` 和 `regression_pass_rate`。

Bad Case regression MVP 口径：

```text
regression_pass_rate = verified_cases / max(fixed_cases + verified_cases + open_cases, 1)
```

当前没有 reopen 机制，因此 `reopened_case_count` 返回 0。该指标不是
rerun-based regression，也不代表真实模型回归通过率。

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

## 与 Bad Case / Review 的边界

Evaluation failed cases 是评测失败记录，不等于 Bad Case Center 的
`bad_cases.jsonl`。Stage 8HI 提供显式转换 MVP：调用
`POST /api/bad-cases/from-failed-case` 后创建 `source=evaluation_center`、
`linked_failed_case_id=<failed_case_id>` 的 Bad Case。该操作不会修改
`failed_cases.jsonl`、`evaluation_results.jsonl` 或原始 Review artifacts。

Review Center 的 `false_positive` / `false_negative` 是人工复核状态，也不是
Evaluation ground truth。Evaluation 可以读取 Stage 6/7 artifacts，但不修改
Review artifacts。
